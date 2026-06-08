from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password: str
    referral_code: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    is_admin: bool
    is_active: bool
    balance: float
    total_invested: float
    total_profit: float
    referral_code: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class PlanOut(BaseModel):
    id: int
    name: str
    slug: str
    min_amount: float
    max_amount: Optional[float]
    daily_return_pct: float
    duration_days: int
    description: Optional[str]
    features: Optional[str]
    color: str
    icon: str

    class Config:
        from_attributes = True


class InvestmentCreate(BaseModel):
    plan_id: int
    amount: float


class InvestmentOut(BaseModel):
    id: int
    amount: float
    profit_accrued: float
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    plan: PlanOut

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    type: str
    amount: float
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WithdrawalCreate(BaseModel):
    amount: float
    wallet_address: str
    network: str = "TRC20"


class WithdrawalOut(BaseModel):
    id: int
    amount: float
    wallet_address: str
    network: str
    status: str
    admin_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DepositCreate(BaseModel):
    amount: float
    tx_hash: Optional[str] = None
    wallet_from: Optional[str] = None


class AdminUserUpdate(BaseModel):
    balance: Optional[float] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_admin: Optional[bool] = None


class WithdrawalAction(BaseModel):
    status: str
    admin_note: Optional[str] = None


class StatsOut(BaseModel):
    total_users: int
    total_invested: float
    total_profit_paid: float
    active_investments: int
    pending_withdrawals: int
    total_balance: float
