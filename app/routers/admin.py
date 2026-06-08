from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from ..database import get_db
from .. import models, schemas
from ..auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    total_users = db.query(func.count(models.User.id)).scalar()
    total_invested = db.query(func.sum(models.User.total_invested)).scalar() or 0
    total_profit = db.query(func.sum(models.User.total_profit)).scalar() or 0
    active_inv = db.query(func.count(models.Investment.id)).filter(
        models.Investment.status == "active"
    ).scalar()
    pending_wd = db.query(func.count(models.WithdrawalRequest.id)).filter(
        models.WithdrawalRequest.status == "pending"
    ).scalar()
    total_balance = db.query(func.sum(models.User.balance)).scalar() or 0

    return schemas.StatsOut(
        total_users=total_users,
        total_invested=total_invested,
        total_profit_paid=total_profit,
        active_investments=active_inv,
        pending_withdrawals=pending_wd,
        total_balance=total_balance,
    )


@router.get("/users")
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [schemas.UserOut.model_validate(u) for u in users]


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    data: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.balance is not None:
        diff = data.balance - user.balance
        user.balance = data.balance
        if diff != 0:
            tx = models.Transaction(
                user_id=user.id,
                type="bonus" if diff > 0 else "withdrawal",
                amount=abs(diff),
                status="completed",
                description="Admin balance adjustment",
            )
            db.add(tx)
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_verified is not None:
        user.is_verified = data.is_verified
    if data.is_admin is not None:
        user.is_admin = data.is_admin

    db.commit()
    return schemas.UserOut.model_validate(user)


@router.get("/withdrawals")
def list_withdrawals(
    status: str = "pending",
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    q = db.query(models.WithdrawalRequest)
    if status != "all":
        q = q.filter(models.WithdrawalRequest.status == status)
    return [schemas.WithdrawalOut.model_validate(w) for w in q.order_by(
        models.WithdrawalRequest.created_at.desc()
    ).all()]


@router.patch("/withdrawals/{wr_id}")
def process_withdrawal(
    wr_id: int,
    data: schemas.WithdrawalAction,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    wr = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == wr_id).first()
    if not wr:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if wr.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")

    wr.status = data.status
    wr.admin_note = data.admin_note
    wr.processed_at = datetime.utcnow()

    tx = db.query(models.Transaction).filter(
        models.Transaction.user_id == wr.user_id,
        models.Transaction.type == "withdrawal",
        models.Transaction.status == "pending",
    ).order_by(models.Transaction.created_at.desc()).first()

    if data.status == "rejected" and tx:
        tx.status = "rejected"
        user = db.query(models.User).filter(models.User.id == wr.user_id).first()
        if user:
            user.balance += wr.amount
    elif data.status == "completed" and tx:
        tx.status = "completed"
        user = db.query(models.User).filter(models.User.id == wr.user_id).first()
        if user:
            user.total_profit += wr.amount

    db.commit()
    return schemas.WithdrawalOut.model_validate(wr)


@router.post("/accrue-profits")
def accrue_profits(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    now = datetime.utcnow()
    active = db.query(models.Investment).filter(models.Investment.status == "active").all()
    count = 0

    for inv in active:
        if inv.end_date and now > inv.end_date:
            inv.status = "completed"
            db.add(models.Transaction(
                user_id=inv.user_id,
                type="profit",
                amount=inv.profit_accrued,
                status="completed",
                description=f"Investment #{inv.id} completed — profit credited",
            ))
            inv.user.balance += inv.amount + inv.profit_accrued
            inv.user.total_profit += inv.profit_accrued
            count += 1
            continue

        days = max(1, (now - inv.last_accrual).total_seconds() / 86400)
        daily_pct = inv.plan.daily_return_pct / 100
        profit = inv.amount * daily_pct * days
        inv.profit_accrued += profit
        inv.last_accrual = now
        inv.user.balance += profit
        inv.user.total_profit += profit

        db.add(models.Transaction(
            user_id=inv.user_id,
            type="profit",
            amount=profit,
            status="completed",
            description=f"Daily profit from {inv.plan.name} plan",
        ))
        count += 1

    db.commit()
    return {"message": f"Processed {count} investments"}


@router.get("/deposits")
def list_deposits(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    deposits = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.type == "deposit",
            models.Transaction.status == "pending",
            models.Transaction.amount > 0,
        )
        .order_by(models.Transaction.created_at.desc())
        .all()
    )
    return [schemas.TransactionOut.model_validate(d) for d in deposits]


@router.patch("/deposits/{tx_id}")
def approve_deposit(
    tx_id: int,
    data: schemas.WithdrawalAction,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not tx or tx.status != "pending":
        raise HTTPException(status_code=404, detail="Transaction not found or already processed")

    tx.status = data.status
    if data.status == "completed":
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()
        if user:
            user.balance += tx.amount

    db.commit()
    return schemas.TransactionOut.model_validate(tx)
