from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user

router = APIRouter(prefix="/api", tags=["investments"])


@router.get("/plans", response_model=list[schemas.PlanOut])
def get_plans(db: Session = Depends(get_db)):
    return db.query(models.InvestmentPlan).filter(models.InvestmentPlan.is_active == True).all()


@router.post("/invest", response_model=schemas.InvestmentOut)
def create_investment(
    data: schemas.InvestmentCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(models.InvestmentPlan).filter(
        models.InvestmentPlan.id == data.plan_id,
        models.InvestmentPlan.is_active == True,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if data.amount < plan.min_amount:
        raise HTTPException(status_code=400, detail=f"Minimum amount is ${plan.min_amount:.0f}")
    if plan.max_amount and data.amount > plan.max_amount:
        raise HTTPException(status_code=400, detail=f"Maximum amount is ${plan.max_amount:.0f}")
    if user.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    user.balance -= data.amount
    user.total_invested += data.amount

    investment = models.Investment(
        user_id=user.id,
        plan_id=plan.id,
        amount=data.amount,
        status="active",
        end_date=datetime.utcnow() + timedelta(days=plan.duration_days),
    )
    db.add(investment)

    tx = models.Transaction(
        user_id=user.id,
        type="deposit",
        amount=-data.amount,
        status="completed",
        description=f"Investment in {plan.name} plan",
    )
    db.add(tx)
    db.commit()
    db.refresh(investment)
    return investment


@router.post("/deposit")
def request_deposit(
    data: schemas.DepositCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum deposit is $100")

    tx = models.Transaction(
        user_id=user.id,
        type="deposit",
        amount=data.amount,
        status="pending",
        description=f"Deposit request. TX: {data.tx_hash or 'N/A'}",
    )
    db.add(tx)
    db.commit()
    return {"message": "Deposit request submitted. Awaiting confirmation.", "tx_id": tx.id}


@router.post("/withdraw", response_model=schemas.WithdrawalOut)
def request_withdrawal(
    data: schemas.WithdrawalCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.amount < 10:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is $10")
    if user.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    user.balance -= data.amount

    wr = models.WithdrawalRequest(
        user_id=user.id,
        amount=data.amount,
        wallet_address=data.wallet_address,
        network=data.network,
        status="pending",
    )
    db.add(wr)

    tx = models.Transaction(
        user_id=user.id,
        type="withdrawal",
        amount=-data.amount,
        status="pending",
        description=f"Withdrawal to {data.wallet_address[:10]}... ({data.network})",
    )
    db.add(tx)
    db.commit()
    db.refresh(wr)
    return wr
