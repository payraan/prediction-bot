# src/core/services/ghost_bot.py
import random
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.database.models import Round, RoundStatus, BetDirection, User, Balance
from src.core.services.user_service import get_or_create_user
from src.core.services.betting_service import place_bet

settings = get_settings()


async def ensure_ghost_user(session: AsyncSession) -> User:
    """Ensure ghost bot user exists with balance"""
    ghost = await get_or_create_user(
        session=session,
        telegram_id=settings.ghost_bot_telegram_id,
        username="ghost_liquidity_bot",
        first_name="GhostBot"
    )
    
    # Ensure balance exists
    res = await session.execute(select(Balance).where(Balance.user_id == ghost.id))
    bal = res.scalar_one_or_none()
    if not bal:
        bal = Balance(
            user_id=ghost.id,
            available=Decimal("0"),
            locked=Decimal("0"),
            currency="TON"
        )
        session.add(bal)
        await session.commit()
    
    return ghost


def _pool_ratio(minority: Decimal, total: Decimal) -> Decimal:
    """Calculate minority pool ratio"""
    if total <= 0:
        return Decimal("0")
    return minority / total


async def maybe_place_ghost_bet(session: AsyncSession, round_id):
    """
    Place ghost bet if needed to balance liquidity
    
    Rules:
    - Only if minority pool < 30%
    - Bet size: 1-5 TON (random)
    - Max exposure: 20% of total pool
    - Min time left: 60 seconds
    """
    if not settings.ghost_bot_enabled:
        return {"placed": False, "reason": "disabled"}
    
    # Get round
    res = await session.execute(select(Round).where(Round.id == round_id))
    rnd = res.scalar_one_or_none()
    if not rnd or rnd.status != RoundStatus.BETTING_OPEN:
        return {"placed": False, "reason": "no_open_round"}
    
    # Check time left
    now = datetime.utcnow()
    time_left = int((rnd.betting_end_at - now).total_seconds())
    if time_left < settings.ghost_bot_min_time_left_seconds:
        return {"placed": False, "reason": "too_late"}
    
    # Calculate pools
    total_up = Decimal(rnd.total_up_amount or 0)
    total_down = Decimal(rnd.total_down_amount or 0)
    total = total_up + total_down
    
    # If pool is empty, wait for real users
    if total <= Decimal("0"):
        return {"placed": False, "reason": "empty_pool"}
    
    # Identify minority side
    if total_up <= total_down:
        minority_dir = BetDirection.UP
        minority_amt = total_up
    else:
        minority_dir = BetDirection.DOWN
        minority_amt = total_down
    
    minority_ratio = _pool_ratio(minority_amt, total)
    
    # Check if minority needs help
    if minority_ratio >= Decimal(str(settings.ghost_bot_minority_threshold)):
        return {"placed": False, "reason": "balanced_enough"}
    
    # Calculate bet amount with exposure cap
    max_exposure = Decimal(str(settings.ghost_bot_max_round_exposure)) * total
    bet_amt = Decimal(str(random.uniform(
        settings.ghost_bot_min_bet,
        settings.ghost_bot_max_bet
    ))).quantize(Decimal("0.01"))
    
    if bet_amt > max_exposure:
        bet_amt = max_exposure.quantize(Decimal("0.01"))
    
    if bet_amt <= 0:
        return {"placed": False, "reason": "exposure_cap"}
    
    # Get ghost user
    ghost = await ensure_ghost_user(session)
    
    # Check balance
    bal_res = await session.execute(select(Balance).where(Balance.user_id == ghost.id))
    bal = bal_res.scalar_one()
    if bal.available < bet_amt:
        return {"placed": False, "reason": "ghost_insufficient_balance"}
    
    # Choose direction: 80% minority, 20% random (for trust)
    if random.random() < 0.20:
        chosen_dir = random.choice([BetDirection.UP, BetDirection.DOWN])
    else:
        chosen_dir = minority_dir
    
    # Place bet
    try:
        result = await place_bet(
            session=session,
            telegram_id=ghost.telegram_id,
            round_id=str(rnd.id),
            direction=chosen_dir.value,
            amount=float(bet_amt)
        )
        return {
            "placed": True,
            "direction": chosen_dir.value,
            "amount": float(bet_amt),
            "result": result
        }
    except Exception as e:
        return {"placed": False, "reason": f"error:{e}"}
