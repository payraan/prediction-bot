import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Market, MarketType, MarketStatus,
    Prediction, PredictionDirection, PredictionStatus,
    MarketResolution, Balance, Ledger, LedgerEventType
)

HOUSE_FEE_RATE = Decimal("0.05")  # ۵ درصد کارمزد پلتفرم از استخر بازنده‌ها

async def create_local_market(
    session: AsyncSession,
    title: str,
    closes_at: datetime,
    description: str = None,
    category: str = "GENERAL",
    admin_id: uuid.UUID = None
) -> Market:
    """ایجاد یک بازار بومی جدید توسط ادمین"""
    new_market = Market(
        title=title,
        description=description,
        category=category,
        market_type=MarketType.LOCAL,
        status=MarketStatus.ACTIVE,
        closes_at=closes_at,
        created_by=admin_id
    )
    session.add(new_market)
    await session.commit()
    await session.refresh(new_market)
    return new_market

async def get_active_local_markets(session: AsyncSession):
    """گرفتن لیست بازارهای فعال بومی"""
    stmt = select(Market).where(
        Market.market_type == MarketType.LOCAL,
        Market.status == MarketStatus.ACTIVE
    )
    result = await session.execute(stmt)
    return result.scalars().all()

async def place_prediction(
    session: AsyncSession,
    user_id: uuid.UUID,
    market_id: uuid.UUID,
    direction: PredictionDirection,
    amount: Decimal
) -> Prediction:
    """ثبت پیش‌بینی توسط کاربر با رعایت Locking دیتابیس"""
    
    # ۱. چک کردن وضعیت بازار
    market = await session.get(Market, market_id)
    if not market or market.status != MarketStatus.ACTIVE:
        raise ValueError("Market is not active or does not exist")
    
    if amount < market.min_prediction_amount or amount > market.max_prediction_amount:
        raise ValueError("Amount out of allowed range")

    # ۲. قفل کردن رکورد موجودی کاربر (Row-level Lock) برای جلوگیری از Double-Spend
    stmt = select(Balance).where(
        Balance.user_id == user_id,
        Balance.asset == "TON"  # فعلاً مبنای پولی شبکه را TON در نظر می‌گیریم
    ).with_for_update()
    
    balance_result = await session.execute(stmt)
    balance = balance_result.scalar_one_or_none()
    
    if not balance or balance.available < amount:
        raise ValueError("Insufficient available balance")

    # ۳. کسر از موجودی در دسترس و انتقال به موجودی قفل شده
    balance.available -= amount
    balance.locked += amount

    # ۴. آپدیت استخر مالی بازار
    if direction == PredictionDirection.YES:
        market.total_pool_yes += amount
    else:
        market.total_pool_no += amount

    # ۵. ایجاد رکورد پیش‌بینی
    prediction = Prediction(
        user_id=user_id,
        market_id=market_id,
        account_context="real",
        direction=direction,
        amount=amount
    )
    session.add(prediction)
    await session.flush()  # برای گرفتن ID پیش‌بینی

    # ۶. ثبت در دفتر کل (Ledger)
    ledger_entry = Ledger(
        user_id=user_id,
        event_type=LedgerEventType.BET_LOCK,
        amount=amount,
        currency=balance.currency,
        asset=balance.asset,
        network=balance.network,
        available_before=balance.available + amount,
        available_after=balance.available,
        locked_before=balance.locked - amount,
        locked_after=balance.locked,
        description=f"Locked for prediction {prediction.id} on market {market_id}",
        idempotency_key=f"LOCK:{market_id}:{prediction.id}"
    )
    session.add(ledger_entry)

    await session.commit()
    return prediction

async def propose_resolution(
    session: AsyncSession,
    market_id: uuid.UUID,
    outcome: str,
    admin_id: uuid.UUID,
    evidence_url: str = None
) -> MarketResolution:
    """اعلام نتیجه بازار توسط ادمین و رفتن به فاز انتظار (شفافیت)"""
    market = await session.get(Market, market_id)
    if not market or market.status != MarketStatus.ACTIVE:
        raise ValueError("Market is not ready for resolution")

    market.status = MarketStatus.PENDING_RESOLUTION
    
    resolution = MarketResolution(
        market_id=market_id,
        outcome=outcome,
        resolved_by=admin_id,
        evidence_url=evidence_url,
        dispute_deadline=datetime.utcnow() + timedelta(hours=24)
    )
    session.add(resolution)
    await session.commit()
    await session.refresh(resolution)
    return resolution

async def finalize_market(session: AsyncSession, market_id: uuid.UUID) -> dict:
    """تسویه نهایی بازار و توزیع سود با رعایت Idempotency"""
    
    market = await session.get(Market, market_id)
    if not market or market.status != MarketStatus.PENDING_RESOLUTION:
        raise ValueError("Market is not in pending resolution status")

    stmt = select(MarketResolution).where(MarketResolution.market_id == market_id)
    res_result = await session.execute(stmt)
    resolution = res_result.scalar_one_or_none()
    
    if not resolution:
        raise ValueError("Resolution data not found")

    winning_direction = PredictionDirection.YES if resolution.outcome == "YES" else PredictionDirection.NO
    
    total_winning_pool = market.total_pool_yes if winning_direction == PredictionDirection.YES else market.total_pool_no
    total_losing_pool = market.total_pool_no if winning_direction == PredictionDirection.YES else market.total_pool_yes
    
    # محاسبه کارمزد پلتفرم از استخر بازنده‌ها
    house_fee_amount = total_losing_pool * HOUSE_FEE_RATE
    net_losing_pool = total_losing_pool - house_fee_amount

    # گرفتن تمام پیش‌بینی‌های این بازار
    pred_stmt = select(Prediction).where(Prediction.market_id == market_id)
    predictions = (await session.execute(pred_stmt)).scalars().all()

    total_payouts = Decimal("0")

    for pred in predictions:
        # دوباره موجودی کاربر را با لاک می‌گیریم
        bal_stmt = select(Balance).where(
            Balance.user_id == pred.user_id,
            Balance.asset == "TON"
        ).with_for_update()
        balance = (await session.execute(bal_stmt)).scalar_one_or_none()
        
        if not balance:
            continue
            
        # آزادسازی مقدار قفل شده در هر صورت (چه برد چه باخت)
        balance.locked -= pred.amount

        if pred.direction == winning_direction:
            # کاربر برنده شده است
            user_share_pct = pred.amount / total_winning_pool if total_winning_pool > 0 else Decimal("0")
            profit = net_losing_pool * user_share_pct
            payout = pred.amount + profit
            
            balance.available += payout
            pred.status = PredictionStatus.WON
            pred.is_correct = True
            pred.payout = payout
            total_payouts += payout

            # ثبت لجر برد با کلید Idempotency
            session.add(Ledger(
                user_id=pred.user_id,
                event_type=LedgerEventType.SETTLE_WIN,
                amount=payout,
                currency=balance.currency,
                asset=balance.asset,
                network=balance.network,
                description=f"Won prediction {pred.id} on market {market_id}",
                idempotency_key=f"MARKET_PAYOUT:{market_id}:{pred.id}"
            ))
        else:
            # کاربر باخته است
            pred.status = PredictionStatus.LOST
            pred.is_correct = False
            pred.payout = Decimal("0")

            session.add(Ledger(
                user_id=pred.user_id,
                event_type=LedgerEventType.SETTLE_LOSS,
                amount=pred.amount,
                currency=balance.currency,
                asset=balance.asset,
                network=balance.network,
                description=f"Lost prediction {pred.id} on market {market_id}",
                idempotency_key=f"MARKET_LOSS:{market_id}:{pred.id}"
            ))

    # ثبت کارمزد پلتفرم در لجر (همانطور که کلاد خواسته بود)
    if house_fee_amount > 0:
        session.add(Ledger(
            event_type=LedgerEventType.HOUSE_FEE,
            amount=house_fee_amount,
            currency="TON",
            asset="TON",
            network="TON",
            description=f"House fee for market {market_id}",
            idempotency_key=f"HOUSE_FEE:{market_id}"
        ))

    market.status = MarketStatus.RESOLVED
    resolution.is_finalized = True
    resolution.finalized_at = datetime.utcnow()

    await session.commit()
    
    return {
        "market_id": market_id,
        "winning_pool": str(total_winning_pool),
        "house_fee": str(house_fee_amount),
        "total_payouts": str(total_payouts)
    }
