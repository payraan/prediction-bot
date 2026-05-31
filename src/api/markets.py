import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session
from src.api.auth import get_current_user
from src.core.services.local_market_service import get_active_local_markets, place_prediction
from src.database.models import PredictionDirection

router = APIRouter(prefix="/api/markets", tags=["Local Markets"])

# Dependency
async def get_db():
    async with async_session() as session:
        yield session

class PredictionRequest(BaseModel):
    direction: PredictionDirection
    amount: Decimal

@router.get("/local")
async def get_local_markets(db: AsyncSession = Depends(get_db)):
    """دریافت لیست بازارهای فعال بومی"""
    markets = await get_active_local_markets(db)
    return {"markets": markets}

@router.post("/local/{market_id}/predict")
async def create_prediction(market_id: uuid.UUID, req: PredictionRequest, db: AsyncSession = Depends(get_db), user_data: dict = Depends(get_current_user)):
    """ثبت پیش‌بینی روی یک بازار بومی"""
    from sqlalchemy import select
    from src.database.models import User
    result = await db.execute(select(User).where(User.telegram_id == user_data["id"]))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        prediction = await place_prediction(
            session=db,
            user_id=db_user.id,
            market_id=market_id,
            direction=req.direction,
            amount=req.amount
        )
        return {"status": "success", "prediction_id": prediction.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get('/active')
async def get_active_markets_fallback(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Market).where(Market.status == MarketStatus.ACTIVE))
    return result.scalars().all()
