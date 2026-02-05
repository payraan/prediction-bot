"""
Leaderboard API
API برای لیدربورد و آمار کاربران
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session
from src.database.models import User, UserStats
from src.core.services.user_service import get_or_create_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    telegram_id: int
    username: Optional[str]
    wins: int
    losses: int
    score: float
    win_rate: float


class UserStatsResponse(BaseModel):
    wins: int
    losses: int
    ties: int
    total_bets: int
    score: float
    net_pnl: float
    win_streak: int
    best_streak: int
    win_rate: float


@router.get("/top", response_model=List[LeaderboardEntry])
async def get_leaderboard(limit: int = 50, offset: int = 0):
    """
    دریافت لیست برترین‌ها
    
    - limit: حداکثر 50
    - offset: برای pagination
    """
    limit = min(max(limit, 1), 50)
    
    async with async_session() as session:
        query = (
            select(
                User.username,
                User.telegram_id,
                UserStats.wins,
                UserStats.losses,
                UserStats.total_bets,
                UserStats.score
            )
            .join(UserStats, UserStats.user_id == User.id)
            .where(UserStats.total_bets > 0)
            .where(User.is_system_user == False)
            .order_by(desc(UserStats.score))
            .limit(limit)
            .offset(offset)
        )
        
        result = await session.execute(query)
        rows = result.all()
    
    return [
        LeaderboardEntry(
            rank=offset + i + 1,
            telegram_id=row.telegram_id,
            username=row.username,
            wins=row.wins,
            losses=row.losses,
            score=float(row.score),
            win_rate=round(row.wins / row.total_bets * 100, 1) if row.total_bets > 0 else 0
        )
        for i, row in enumerate(rows)
    ]


@router.get("/me", response_model=UserStatsResponse)
async def get_my_stats(telegram_id: int):
    """
    دریافت آمار کاربر فعلی
    
    - telegram_id: از initData گرفته می‌شود
    """
    async with async_session() as session:
        user = await get_or_create_user(session, telegram_id=telegram_id)
        
        query = select(UserStats).where(UserStats.user_id == user.id)
        result = await session.execute(query)
        stats = result.scalar_one_or_none()
        
        if not stats:
            return UserStatsResponse(
                wins=0,
                losses=0,
                ties=0,
                total_bets=0,
                score=0,
                net_pnl=0,
                win_streak=0,
                best_streak=0,
                win_rate=0
            )
        
        return UserStatsResponse(
            wins=stats.wins,
            losses=stats.losses,
            ties=stats.ties,
            total_bets=stats.total_bets,
            score=float(stats.score),
            net_pnl=float(stats.net_pnl),
            win_streak=stats.win_streak,
            best_streak=stats.best_streak,
            win_rate=round(stats.wins / stats.total_bets * 100, 1) if stats.total_bets > 0 else 0
        )
