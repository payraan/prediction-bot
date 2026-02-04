"""
Stats Service
محاسبه و به‌روزرسانی آمار کاربران برای لیدربورد
"""
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import UserStats


async def ensure_user_stats(session: AsyncSession, user_id: uuid.UUID) -> UserStats:
    """اطمینان از وجود stats برای کاربر"""
    res = await session.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = res.scalar_one_or_none()
    
    if stats:
        return stats
    
    stats = UserStats(
        user_id=user_id,
        wins=0,
        losses=0,
        ties=0,
        total_bets=0,
        net_pnl=Decimal("0"),
        win_streak=0,
        best_streak=0,
        score=Decimal("0")
    )
    session.add(stats)
    await session.commit()
    return stats


def compute_score(stats: UserStats) -> Decimal:
    """
    محاسبه امتیاز کاربر
    
    فرمول: (wins * 3) + (win_streak * 0.5) + (net_pnl * 0.1) - (losses * 1)
    """
    return (
        Decimal(stats.wins) * Decimal("3")
        + Decimal(stats.win_streak) * Decimal("0.5")
        + Decimal(stats.net_pnl) * Decimal("0.1")
        - Decimal(stats.losses) * Decimal("1")
    )


async def apply_bet_result(
    session: AsyncSession,
    user_id: uuid.UUID,
    outcome: str,  # "WIN" | "LOSS" | "TIE"
    pnl_delta: Decimal,  # تغییر سود/زیان
):
    """
    اعمال نتیجه یک شرط به آمار کاربر
    
    این تابع بعد از settle_round صدا زده می‌شود
    """
    stats = await ensure_user_stats(session, user_id)
    
    stats.total_bets += 1
    stats.net_pnl = (stats.net_pnl or Decimal("0")) + pnl_delta
    
    if outcome == "WIN":
        stats.wins += 1
        stats.win_streak += 1
        if stats.win_streak > stats.best_streak:
            stats.best_streak = stats.win_streak
    
    elif outcome == "LOSS":
        stats.losses += 1
        stats.win_streak = 0
    
    else:  # TIE
        stats.ties += 1
        # در حالت TIE، streak را تغییر نمی‌دهیم
    
    # محاسبه امتیاز جدید
    stats.score = compute_score(stats)
    
    await session.commit()
