import uuid
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session
from src.api.auth import get_current_user
from src.core.services.local_market_service import get_active_local_markets, place_prediction
from src.database.models import Market, MarketStatus, MarketType, PredictionDirection

router = APIRouter(prefix="/api/markets", tags=["Markets"])


async def get_db():
    async with async_session() as session:
        yield session


class PredictionRequest(BaseModel):
    direction: PredictionDirection
    amount: Decimal


# ── NEW endpoint your frontend actually calls ─────────────────────────────────

@router.get("/active")
async def get_active_markets(db: AsyncSession = Depends(get_db)):
    """
    Returns ALL active markets: both LOCAL and POLYMARKET.
    This is what the frontend calls via getActiveMarkets().
    """
    stmt = (
        select(Market)
        .where(
            Market.status == MarketStatus.ACTIVE,
            # Only return markets that haven't closed yet
            Market.closes_at > datetime.utcnow(),
        )
        .order_by(Market.closes_at.asc())
        .limit(300) # افزایش لیمیت برای نمایش همه مارکت‌ها از جمله کریپتو
    )
    result = await db.execute(stmt)
    markets = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "title": m.title,
            "description": m.description,
            "category": m.category,
            "market_type": m.market_type,
            "yes_price": float(m.yes_price) if m.yes_price is not None else 0.5,
            "no_price": float(m.no_price) if m.no_price is not None else 0.5,
            "total_pool_yes": float(m.total_pool_yes or 0),
            "total_pool_no": float(m.total_pool_no or 0),
            "closes_at": m.closes_at.isoformat() if m.closes_at else None,
            "eligible_for_prop": m.eligible_for_prop,
        }
        for m in markets
    ]


# ── existing endpoints (kept exactly as they were) ────────────────────────────

@router.get("/local")
async def get_local_markets(db: AsyncSession = Depends(get_db)):
    """Returns only LOCAL markets (admin-created)."""
    markets = await get_active_local_markets(db)
    return {"markets": markets}


@router.post("/local/{market_id}/predict")
async def create_prediction(
    market_id: uuid.UUID,
    req: PredictionRequest,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(get_current_user),
):
    from sqlalchemy import select
    from src.database.models import User

    result = await db.execute(
        select(User).where(User.telegram_id == user_data["id"])
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        prediction = await place_prediction(
            session=db,
            user_id=db_user.id,
            market_id=market_id,
            direction=req.direction,
            amount=req.amount,
        )
        return {"status": "success", "prediction_id": prediction.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
