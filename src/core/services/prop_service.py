import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Market, PropAccount, PropStatus, PropPhase, 
    Prediction, PredictionStatus, PredictionDirection, 
    DailyEquitySnapshot, Balance, Ledger, LedgerEventType
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

# قیمت چالش‌ها
CHALLENGE_PRICES = {
    Decimal("10000"): Decimal("50"),   # چالش ۱۰ هزار دلاری -> ۵۰ تتر/تون
    Decimal("25000"): Decimal("125"),  # چالش ۲۵ هزار دلاری -> ۱۲۵ تتر/تون
}

async def buy_prop_challenge(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_size: Decimal
) -> PropAccount:
    """خرید چالش پراپ با کسر موجودی واقعی"""
    if account_size not in CHALLENGE_PRICES:
        raise ValueError("Invalid account size. Available sizes: 10000, 25000")
        
    fee = CHALLENGE_PRICES[account_size]
    
    # قفل کردن موجودی واقعی (برای مثال روی USDT تنظیم شده)
    stmt = select(Balance).where(Balance.user_id == user_id, Balance.asset == "USDT").with_for_update()
    balance = (await session.execute(stmt)).scalar_one_or_none()
    
    if not balance or balance.available < fee:
        raise ValueError(f"Insufficient real balance. You need {fee} USDT to buy this challenge.")
        
    # کسر هزینه چالش
    balance.available -= fee
    
    # ساخت اکانت پراپ فاز ۱
    prop_account = PropAccount(
        user_id=user_id,
        phase=PropPhase.PHASE1,
        status=PropStatus.ACTIVE
    )
    # پر کردن تمام فیلدهای اجباری دیتابیس
    prop_account.starting_balance = account_size
    prop_account.virtual_balance = account_size
    prop_account.peak_balance = account_size
    prop_account.target_profit_pct = PHASE_1_TARGET
    prop_account.max_daily_drawdown_pct = MAX_DAILY_DD
    prop_account.max_total_drawdown_pct = MAX_TOTAL_DD
    prop_account.challenge_fee = fee
    prop_account.challenge_fee_asset = "USDT" 
    session.add(prop_account)
    await session.flush()  # برای دریافت آیدی اکانت
    
    # ثبت اسنپ‌شات روزانه اولیه برای محاسبه Drawdown
    snapshot = DailyEquitySnapshot(
        prop_account_id=prop_account.id,
        start_of_day_equity=account_size
    )
    session.add(snapshot)
    
    # ثبت رویداد در لجر (درآمد پلتفرم)
    ledger = Ledger(
        user_id=user_id,
        event_type=LedgerEventType.HOUSE_FEE,
        amount=-fee,
        currency="USDT",
        asset="USDT",
        network=balance.network,
        description=f"Purchased ${account_size} Prop Challenge",
        idempotency_key=f"PROP_BUY:{prop_account.id}"
    )
    session.add(ledger)
    
    await session.commit()
    return prop_account


async def place_prop_prediction(
    session: AsyncSession,
    prop_account_id: uuid.UUID,
    market_id: uuid.UUID,
    direction: PredictionDirection,
    amount: Decimal
) -> Prediction:
    """ثبت پیش‌بینی با پول مجازی پراپ (همراه با فیلترهای ضدقمار)"""
    
    stmt_acc = select(PropAccount).where(PropAccount.id == prop_account_id).with_for_update()
    acc_result = await session.execute(stmt_acc)
    prop_account = acc_result.scalar_one_or_none()

    if not prop_account or prop_account.status != PropStatus.ACTIVE:
        raise ValueError("Prop account is not active or does not exist.")

    market = await session.get(Market, market_id)
    if not market or not market.eligible_for_prop:
        raise ValueError("Market is not eligible for prop trading.")
    
    current_price = market.yes_price if direction == PredictionDirection.YES else market.no_price

    if current_price < MIN_ODDS or current_price > MAX_ODDS:
        raise ValueError(f"Odds must be between {MIN_ODDS} and {MAX_ODDS}. Current: {current_price}")

    max_allowed_risk = prop_account.starting_balance * MAX_RISK_PCT
    if amount > max_allowed_risk:
        raise ValueError(f"Max risk exceeded. You can only risk up to {max_allowed_risk} on a single market.")

    if prop_account.virtual_balance < amount:
        raise ValueError("Insufficient virtual balance.")

    stmt_open_trades = select(func.count(Prediction.id)).where(
        Prediction.prop_account_id == prop_account_id,
        Prediction.status == PredictionStatus.OPEN
    )
    open_trades_count = (await session.execute(stmt_open_trades)).scalar()
    
    if open_trades_count >= MAX_OPEN_TRADES:
        raise ValueError(f"Maximum of {MAX_OPEN_TRADES} concurrent open trades reached.")

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


async def evaluate_prop_accounts(session: AsyncSession):
    """موتور ارزیاب: بررسی مداوم وضعیت اکانت‌ها (Drawdown و Target)"""
    stmt = select(PropAccount).where(PropAccount.status == PropStatus.ACTIVE)
    active_accounts = (await session.execute(stmt)).scalars().all()
    
    for account in active_accounts:
        # محاسبه میزان سرمایه درگیر در پیش‌بینی‌های باز
        stmt_pending = select(func.sum(Prediction.amount)).where(
            Prediction.prop_account_id == account.id,
            Prediction.status == PredictionStatus.OPEN
        )
        pending_amount = (await session.execute(stmt_pending)).scalar() or Decimal("0")
        
        # اکوئیتی لحظه‌ای: موجودی مجازی آزاد + پولی که در بازار درگیر است
        current_equity = account.virtual_balance + pending_amount
        
        # دریافت اکوئیتی شروع روز
        stmt_snap = select(DailyEquitySnapshot).where(
            DailyEquitySnapshot.prop_account_id == account.id
        ).order_by(DailyEquitySnapshot.date.desc()).limit(1)
        snapshot = (await session.execute(stmt_snap)).scalar_one_or_none()
        
        start_of_day_equity = snapshot.start_of_day_equity if snapshot else account.starting_balance
        
        # ۱. بررسی افت روزانه (۴٪)
        daily_dd_limit = start_of_day_equity * (Decimal("1") - MAX_DAILY_DD)
        if current_equity <= daily_dd_limit:
            account.status = PropStatus.BREACHED
            continue
            
        # ۲. بررسی افت کل (۸٪ استاتیک)
        total_dd_limit = account.starting_balance * (Decimal("1") - MAX_TOTAL_DD)
        if current_equity <= total_dd_limit:
            account.status = PropStatus.BREACHED
            continue
            
        # ۳. بررسی تارگت سود (فقط زمانی که هیچ پیش‌بینی بازی وجود نداشته باشد)
        if pending_amount == Decimal("0"):
            if account.phase == PropPhase.PHASE1:
                target = account.starting_balance * (Decimal("1") + PHASE_1_TARGET)
                if current_equity >= target:
                    account.status = PropStatus.PASSED
            elif account.phase == PropPhase.PHASE2:
                target = account.starting_balance * (Decimal("1") + PHASE_2_TARGET)
                if current_equity >= target:
                    account.status = PropStatus.FUNDED
    
    await session.commit()


async def take_daily_snapshots(session: AsyncSession):
    """گرفتن اسنپ‌شات اکوئیتی در ابتدای هر روز برای محاسبه Drawdown"""
    stmt = select(PropAccount).where(PropAccount.status == PropStatus.ACTIVE)
    active_accounts = (await session.execute(stmt)).scalars().all()
    
    for account in active_accounts:
        stmt_pending = select(func.sum(Prediction.amount)).where(
            Prediction.prop_account_id == account.id,
            Prediction.status == PredictionStatus.OPEN
        )
        pending_amount = (await session.execute(stmt_pending)).scalar() or Decimal("0")
        current_equity = account.virtual_balance + pending_amount
        
        snapshot = DailyEquitySnapshot(
            prop_account_id=account.id,
            start_of_day_equity=current_equity
        )
        session.add(snapshot)
        
    await session.commit()
