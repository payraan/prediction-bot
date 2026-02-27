"""
Stats Service
محاسبه و به‌روزرسانی آمار کاربران برای لیدربورد
"""
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import UserStats


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
    IMPORTANT: این تابع داخل تراکنشِ caller اجرا می‌شود و نباید commit/rollback انجام دهد.
    """

    # 1) fetch existing stats row (or create)
    res = await session.execute(
        select(UserStats).where(UserStats.user_id == user_id)
    )
    stats = res.scalar_one_or_none()

    if not stats:
        stats = UserStats(
            user_id=user_id,
            wins=0,
            losses=0,
            ties=0,
            total_bets=0,
            net_pnl=Decimal("0"),
            win_streak=0,
            best_streak=0,
            score=Decimal("0"),
        )
        session.add(stats)
        await session.flush()  # ensure row exists

    # 2) update counters
    stats.total_bets = (stats.total_bets or 0) + 1
    stats.net_pnl = (stats.net_pnl or Decimal("0")) + (pnl_delta or Decimal("0"))

    if outcome == "WIN":
        stats.wins = (stats.wins or 0) + 1
        stats.win_streak = (stats.win_streak or 0) + 1
        if (stats.win_streak or 0) > (stats.best_streak or 0):
            stats.best_streak = stats.win_streak
    elif outcome == "LOSS":
        stats.losses = (stats.losses or 0) + 1
        stats.win_streak = 0
    else:  # "TIE"
        stats.ties = (stats.ties or 0) + 1

    # 3) recompute score (uses your existing compute_score())
    stats.score = compute_score(stats)

    # no commit/rollback here
    return stats
