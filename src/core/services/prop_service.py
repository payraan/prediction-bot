import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Market, PropAccount, PropStatus, PropPhase, 
    Prediction, PredictionStatus, PredictionDirection, DailyEquitySnapshot
)

# === پارامترهای طلایی سیستم پراپ ===
PHASE_1_TARGET = Decimal("0.10")  # ۱۰٪ تارگت فاز ۱
PHASE_2_TARGET = Decimal("0.05")  # ۵٪ تارگت فاز ۲
MAX_TOTAL_DD = Decimal("0.08")    # ۸٪ حداکثر افت کل استاتیک
MAX_DAILY_DD = Decimal("0.04")    # ۴٪ حداکثر افت روزانه
MIN_ODDS = Decimal("0.15")        # حداقل قیمت مجاز (ضد قمار)
MAX_ODDS = Decimal("0.85")        # حداکثر قیمت مجاز (ضد قمار)
MAX_RISK_PCT = Decimal("0.15")    # حداکثر ۱۵٪ سرمایه در یک مارکت
MAX_OPEN_TRADES = 3               # حداکثر ۳ ترید باز همزمان

async def place_prop_prediction(
    session: AsyncSession,
    prop_account_id: uuid.UUID,
    market_id: uuid.UUID,
    direction: PredictionDirection,
    amount: Decimal
) -> Prediction:
    """ثبت پیش‌بینی با پول مجازی پراپ (همراه با فیلترهای ضدقمار)"""
    
    # ۱. واکشی اکانت پراپ با Lock برای جلوگیری از Double Spend
    stmt_acc = select(PropAccount).where(PropAccount.id == prop_account_id).with_for_update()
    acc_result = await session.execute(stmt_acc)
    prop_account = acc_result.scalar_one_or_none()

    if not prop_account or prop_account.status != PropStatus.ACTIVE:
        raise ValueError("Prop account is not active or does not exist.")

    # ۲. واکشی مارکت
    market = await session.get(Market, market_id)
    if not market or not market.eligible_for_prop:
        raise ValueError("Market is not eligible for prop trading.")
    
    # گرفتن قیمت لحظه‌ای
    current_price = market.yes_price if direction == PredictionDirection.YES else market.no_price

    # === اعمال قوانین ضد قمار (Anti-Gambling) ===

    # قانون ۱: فیلتر قیمت (Odds Restriction)
    if current_price < MIN_ODDS or current_price > MAX_ODDS:
        raise ValueError(f"Odds must be between {MIN_ODDS} and {MAX_ODDS}. Current: {current_price}")

    # قانون ۲: حداکثر ریسک ۱۵٪
    max_allowed_risk = prop_account.initial_balance * MAX_RISK_PCT
    if amount > max_allowed_risk:
        raise ValueError(f"Max risk exceeded. You can only risk up to {max_allowed_risk} on a single market.")

    # موجودی مجازی کافی است؟
    if prop_account.virtual_balance < amount:
        raise ValueError("Insufficient virtual balance.")

    # قانون ۳: حداکثر ۳ ترید باز همزمان
    stmt_open_trades = select(func.count(Prediction.id)).where(
        Prediction.prop_account_id == prop_account_id,
        Prediction.status == PredictionStatus.PENDING
    )
    open_trades_count = (await session.execute(stmt_open_trades)).scalar()
    
    if open_trades_count >= MAX_OPEN_TRADES:
        raise ValueError(f"Maximum of {MAX_OPEN_TRADES} concurrent open trades reached.")

    # === کسر از موجودی و ثبت ترید ===
    prop_account.virtual_balance -= amount
    
    prediction = Prediction(
        user_id=prop_account.user_id,
        market_id=market_id,
        prop_account_id=prop_account.id,
        account_context="prop",
        direction=direction,
        amount=amount,
        entry_price=current_price
    )
    
    session.add(prediction)
    await session.commit()
    
    return prediction
