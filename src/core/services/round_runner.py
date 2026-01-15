"""
Round Runner
اجرای خودکار چرخه راندها - نسخه امن نهایی
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update

from src.database.models import Round, RoundStatus
from src.database.connection import async_session
from src.core.services.round_manager import create_round, RoundManagerError
from src.core.services.price_service import get_current_price
from src.core.config import get_settings

settings = get_settings()


async def atomic_lock_round(session, round_id, lock_price: Decimal) -> bool:
    """
    قفل کردن راند به صورت atomic (Optimistic Lock)
    """
    result = await session.execute(
        update(Round)
        .where(Round.id == round_id, Round.status == RoundStatus.BETTING_OPEN)
        .values(
            status=RoundStatus.LOCKED,
            lock_price=lock_price,
            locked_at=datetime.utcnow()
        )
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount > 0


async def atomic_settle_round(session, round_id, settle_price: Decimal) -> bool:
    """
    تسویه راند به صورت atomic با claim-based lock
    با rollback در صورت خطا
    """
    from src.core.services.betting_service import settle_round as settle_bets

    # 1) claim atomically using settled_at as a soft lock
    claim = await session.execute(
        update(Round)
        .where(
            Round.id == round_id,
            Round.status == RoundStatus.LOCKED,
            Round.settled_at == None,  # نسخه امن‌تر
        )
        .values(settled_at=datetime.utcnow())
        .execution_options(synchronize_session=False)
    )
    await session.commit()

    if claim.rowcount == 0:
        return False  # someone else claimed or already settled

    # 2) now we are the claimant - do the actual settle
    try:
        settle_result = await settle_bets(session, round_id, settle_price)
        return settle_result.get("status") != "already_settled"
    except Exception as e:
        # Rollback claim - اجازه بده instance دیگه تلاش کنه
        await session.execute(
            update(Round)
            .where(Round.id == round_id)
            .values(settled_at=None)
            .execution_options(synchronize_session=False)
        )
        await session.commit()
        print(f"خطا در تسویه (claim برگشت خورد): {e}")
        return False


async def process_rounds(asset_symbol: str = "BTCUSDT"):
    """
    پردازش یک سیکل از راندها برای یک asset
    """
    
    async with async_session() as session:
        now = datetime.utcnow()
        
        # گرفتن راند فعال
        result = await session.execute(
            select(Round).where(
                Round.asset_symbol == asset_symbol,
                Round.status.in_([RoundStatus.BETTING_OPEN, RoundStatus.LOCKED])
            ).order_by(Round.round_number.desc())
        )
        current_round = result.scalar_one_or_none()
        
        # حالت ۱: راند فعال نداریم → ساخت راند جدید
        if not current_round:
            print(f"[{asset_symbol}] ساخت راند جدید...")
            try:
                new_round = await create_round(
                    session,
                    asset_symbol=asset_symbol,
                    betting_duration_seconds=settings.round_duration
                )
                print(f"[{asset_symbol}] ✅ راند #{new_round.round_number} ساخته شد")
            except RoundManagerError as e:
                print(f"[{asset_symbol}] ⚠️ {e}")
            except Exception as e:
                print(f"[{asset_symbol}] ❌ خطا در ساخت راند: {e}")
            return
        
        # حالت ۲: راند باز و زمان تموم شده → قفل
        if current_round.status == RoundStatus.BETTING_OPEN:
            if now >= current_round.betting_end_at:
                print(f"[{asset_symbol}] قفل کردن راند #{current_round.round_number}...")
                
                price = await get_current_price(asset_symbol)
                if price:
                    success = await atomic_lock_round(session, current_round.id, price)
                    if success:
                        print(f"[{asset_symbol}] ✅ راند قفل شد با قیمت {price}")
                    else:
                        print(f"[{asset_symbol}] ⚠️ راند قبلاً قفل شده")
                else:
                    print(f"[{asset_symbol}] ❌ خطا در گرفتن قیمت!")
            return
        
        # حالت ۳: راند قفل شده → تسویه
        if current_round.status == RoundStatus.LOCKED:
            lock_time = current_round.locked_at
            settle_delay = settings.round_duration
            
            if lock_time and (now - lock_time).total_seconds() >= settle_delay:
                print(f"[{asset_symbol}] تسویه راند #{current_round.round_number}...")
                
                price = await get_current_price(asset_symbol)
                if price:
                    success = await atomic_settle_round(session, current_round.id, price)
                    if success:
                        print(f"[{asset_symbol}] ✅ راند تسویه شد با قیمت {price}")
                    else:
                        print(f"[{asset_symbol}] ⚠️ راند قبلاً تسویه شده")
                else:
                    print(f"[{asset_symbol}] ❌ خطا در گرفتن قیمت!")
            return


async def run_round_loop(
    assets: list[str] = None,
    interval_seconds: int = 5
):
    """حلقه اصلی اجرای راندها"""
    
    if assets is None:
        assets = ["BTCUSDT"]
    
    print("=" * 50)
    print("🚀 Round Runner شروع شد")
    print(f"   Assets: {assets}")
    print(f"   Check Interval: {interval_seconds}s")
    print(f"   Round Duration: {settings.round_duration}s")
    print("=" * 50)
    
    while True:
        for asset in assets:
            try:
                await process_rounds(asset)
            except Exception as e:
                print(f"[{asset}] ❌ خطای غیرمنتظره: {e}")
        
        await asyncio.sleep(interval_seconds)


async def run_single_cycle(asset_symbol: str = "BTCUSDT"):
    """اجرای یک سیکل (برای تست)"""
    await process_rounds(asset_symbol)


if __name__ == "__main__":
    asyncio.run(run_round_loop())
