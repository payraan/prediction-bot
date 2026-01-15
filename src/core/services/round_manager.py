"""
Round Manager
مدیریت چرخه حیات راندها
"""

import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.database.models import Round, Bet, RoundStatus
from src.core.config import get_settings

settings = get_settings()


class RoundManagerError(Exception):
    """خطای مدیریت راند"""
    pass


async def get_current_round(
    session: AsyncSession,
    asset_symbol: str = "BTCUSDT"
) -> Optional[Round]:
    """گرفتن راند فعال (BETTING_OPEN یا LOCKED)"""
    result = await session.execute(
        select(Round).where(
            Round.asset_symbol == asset_symbol,
            Round.status.in_([RoundStatus.BETTING_OPEN, RoundStatus.LOCKED])
        ).order_by(Round.round_number.desc())
    )
    return result.scalar_one_or_none()


async def get_betting_open_round(
    session: AsyncSession,
    asset_symbol: str = "BTCUSDT"
) -> Optional[Round]:
    """گرفتن راند باز برای شرط‌بندی"""
    result = await session.execute(
        select(Round).where(
            Round.asset_symbol == asset_symbol,
            Round.status == RoundStatus.BETTING_OPEN
        )
    )
    return result.scalar_one_or_none()


async def get_next_round_number(
    session: AsyncSession,
    asset_symbol: str = "BTCUSDT"
) -> int:
    """گرفتن شماره راند بعدی"""
    result = await session.execute(
        select(func.max(Round.round_number)).where(
            Round.asset_symbol == asset_symbol
        )
    )
    max_num = result.scalar()
    return (max_num or 0) + 1


async def create_round(
    session: AsyncSession,
    asset_symbol: str = "BTCUSDT",
    betting_duration_seconds: int = 60
) -> Round:
    """
    ساخت راند جدید
    با handling برای race condition
    """
    
    # چک کنیم راند باز نداشته باشیم
    existing = await get_betting_open_round(session, asset_symbol)
    if existing:
        raise RoundManagerError(f"راند باز برای {asset_symbol} وجود داره")
    
    round_number = await get_next_round_number(session, asset_symbol)
    now = datetime.utcnow()
    
    new_round = Round(
        id=uuid.uuid4(),
        round_number=round_number,
        asset_symbol=asset_symbol,
        status=RoundStatus.BETTING_OPEN,
        betting_start_at=now,
        betting_end_at=now + timedelta(seconds=betting_duration_seconds),
        total_up_amount=Decimal("0"),
        total_down_amount=Decimal("0"),
        house_fee=Decimal("0")
    )
    
    session.add(new_round)
    
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # احتمالاً race condition - راند رو بگیر و برگردون
        existing = await get_betting_open_round(session, asset_symbol)
        if existing:
            return existing
        raise RoundManagerError("خطا در ساخت راند")
    
    return new_round


async def lock_round(
    session: AsyncSession,
    round_id: uuid.UUID,
    lock_price: Decimal
) -> Round:
    """
    قفل کردن راند و ثبت قیمت شروع
    """
    
    result = await session.execute(
        select(Round).where(Round.id == round_id)
    )
    round_obj = result.scalar_one_or_none()
    
    if not round_obj:
        raise RoundManagerError("راند پیدا نشد")
    
    if round_obj.status != RoundStatus.BETTING_OPEN:
        raise RoundManagerError("فقط راند باز قابل قفل شدن است")
    
    round_obj.status = RoundStatus.LOCKED
    round_obj.lock_price = lock_price
    round_obj.locked_at = datetime.utcnow()
    
    await session.commit()
    return round_obj


async def settle_round(
    session: AsyncSession,
    round_id: uuid.UUID,
    settle_price: Decimal
) -> dict:
    """
    تسویه راند - صدا زدن betting_service.settle_round
    """
    from src.core.services.betting_service import settle_round as settle_bets
    
    result = await session.execute(
        select(Round).where(Round.id == round_id)
    )
    round_obj = result.scalar_one_or_none()
    
    if not round_obj:
        raise RoundManagerError("راند پیدا نشد")
    
    if round_obj.status != RoundStatus.LOCKED:
        raise RoundManagerError("فقط راند قفل شده قابل تسویه است")
    
    # صدا زدن سرویس تسویه (که خودش settle_price رو هم ست می‌کنه)
    result = await settle_bets(session, round_id, settle_price)
    
    return result


async def refund_round(
    session: AsyncSession,
    round_id: uuid.UUID,
    reason: str = "کنسل شده"
) -> dict:
    """
    بازگشت همه شرط‌های یک راند (public function)
    """
    from src.core.services.betting_service import _refund_all_bets
    
    result = await session.execute(
        select(Round).where(Round.id == round_id)
    )
    round_obj = result.scalar_one_or_none()
    
    if not round_obj:
        raise RoundManagerError("راند پیدا نشد")
    
    if round_obj.status in [RoundStatus.RESOLVED_UP, RoundStatus.RESOLVED_DOWN, RoundStatus.VOID]:
        return {"status": "already_settled", "round_status": round_obj.status.value}
    
    # گرفتن شرط‌ها
    bets_result = await session.execute(
        select(Bet).where(Bet.round_id == round_id)
    )
    bets = bets_result.scalars().all()
    
    # Refund همه
    result = await _refund_all_bets(session, round_obj, bets)
    
    return result


async def cancel_round(
    session: AsyncSession,
    round_id: uuid.UUID
) -> dict:
    """
    کنسل کردن راند (wrapper برای refund_round)
    """
    return await refund_round(session, round_id, reason="کنسل شده توسط ادمین")


async def get_round_stats(
    session: AsyncSession,
    round_id: uuid.UUID
) -> dict:
    """آمار راند"""
    
    result = await session.execute(
        select(Round).where(Round.id == round_id)
    )
    round_obj = result.scalar_one_or_none()
    
    if not round_obj:
        return None
    
    total_pool = round_obj.total_up_amount + round_obj.total_down_amount
    
    # محاسبه odds
    up_odds = None
    down_odds = None
    if round_obj.total_up_amount > 0:
        up_odds = float(total_pool / round_obj.total_up_amount)
    if round_obj.total_down_amount > 0:
        down_odds = float(total_pool / round_obj.total_down_amount)
    
    return {
        "round_id": str(round_obj.id),
        "round_number": round_obj.round_number,
        "asset": round_obj.asset_symbol,
        "status": round_obj.status.value,
        "total_pool": float(total_pool),
        "up_pool": float(round_obj.total_up_amount),
        "down_pool": float(round_obj.total_down_amount),
        "up_odds": up_odds,
        "down_odds": down_odds,
        "lock_price": float(round_obj.lock_price) if round_obj.lock_price else None,
        "settle_price": float(round_obj.settle_price) if round_obj.settle_price else None,
        "house_fee": float(round_obj.house_fee),
        "betting_end_at": round_obj.betting_end_at.isoformat() if round_obj.betting_end_at else None
    }
