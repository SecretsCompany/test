from .database import SessionLocal
from . import models
from .auth import hash_password, generate_referral_code
import json


PLANS = [
    {
        "name": "Starter",
        "slug": "starter",
        "min_amount": 100,
        "max_amount": 499,
        "daily_return_pct": 1.0,
        "duration_days": 30,
        "description": "Идеально для начинающих инвесторов",
        "features": json.dumps(["1% в день", "30 дней", "От $100", "Ежедневные выплаты", "Поддержка 24/7"]),
        "color": "blue",
        "icon": "seedling",
    },
    {
        "name": "Standard",
        "slug": "standard",
        "min_amount": 500,
        "max_amount": 1999,
        "daily_return_pct": 1.5,
        "duration_days": 30,
        "description": "Оптимальный баланс доходности и риска",
        "features": json.dumps(["1.5% в день", "30 дней", "От $500", "Ежедневные выплаты", "Персональный менеджер"]),
        "color": "green",
        "icon": "chart-line",
    },
    {
        "name": "Premium",
        "slug": "premium",
        "min_amount": 2000,
        "max_amount": 4999,
        "daily_return_pct": 2.0,
        "duration_days": 30,
        "description": "Высокая доходность для опытных инвесторов",
        "features": json.dumps(["2% в день", "30 дней", "От $2 000", "Ежедневные выплаты", "VIP-поддержка", "Аналитика рынка"]),
        "color": "purple",
        "icon": "crown",
    },
    {
        "name": "VIP",
        "slug": "vip",
        "min_amount": 5000,
        "max_amount": None,
        "daily_return_pct": 2.5,
        "duration_days": 30,
        "description": "Максимальная доходность для крупных инвесторов",
        "features": json.dumps(["2.5% в день", "30 дней", "От $5 000", "Ежедневные выплаты", "Выделенный трейдер", "Закрытые сигналы", "Страхование депозита"]),
        "color": "yellow",
        "icon": "gem",
    },
]


def seed_db():
    db = SessionLocal()
    try:
        if db.query(models.InvestmentPlan).count() == 0:
            for p in PLANS:
                db.add(models.InvestmentPlan(**p))
            db.commit()

        if not db.query(models.User).filter(models.User.email == "admin@cryptoinvest.io").first():
            admin = models.User(
                email="admin@cryptoinvest.io",
                full_name="Admin",
                password_hash=hash_password("Admin@12345"),
                is_admin=True,
                is_verified=True,
                referral_code=generate_referral_code(),
                balance=0,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
