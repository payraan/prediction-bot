import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.connection import async_session
from src.database.models import User, PredictionDirection, PropAccount
from src.api.auth import get_current_user
from src.core.services.prop_service import buy_prop_challenge, place_prop_prediction

router = APIRouter(prefix="/api/prop", tags=["Prop Firm"])

async def get_db():
    async with async_session() as session:
        yield session

class BuyChallengeRequest(BaseModel):
    account_size: Decimal  # 10000 or 25000

class PropPredictionRequest(BaseModel):
    prop_account_id: uuid.UUID
    market_id: uuid.UUID
    direction: PredictionDirection
    amount: Decimal

async def get_db_user(db: AsyncSession, telegram_user: dict) -> User:
    stmt = select(User).where(User.telegram_id == telegram_user["id"])
    db_user = (await db.execute(stmt)).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found in DB")
    return db_user

@router.post("/buy")
async def api_buy_challenge(
    req: BuyChallengeRequest, 
    db: AsyncSession = Depends(get_db), 
    telegram_user: dict = Depends(get_current_user)
):
    """خرید چالش پراپ با موجودی واقعی (USDT)"""
    db_user = await get_db_user(db, telegram_user)
    try:
        prop_account = await buy_prop_challenge(db, db_user.id, req.account_size)
        return {"status": "success", "prop_account_id": prop_account.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/predict")
async def api_prop_predict(
    req: PropPredictionRequest, 
    db: AsyncSession = Depends(get_db), 
    telegram_user: dict = Depends(get_current_user)
):
    """ثبت پیش‌بینی روی دیتای پالی‌مارکت با پول مجازی پراپ"""
    db_user = await get_db_user(db, telegram_user)
    try:
        prediction = await place_prop_prediction(
            session=db,
            prop_account_id=req.prop_account_id,
            market_id=req.market_id,
            direction=req.direction,
            amount=req.amount
        )
        return {"status": "success", "prediction_id": prediction.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def api_get_my_prop(db: AsyncSession = Depends(get_db), telegram_user: dict = Depends(get_current_user)):
    """دریافت وضعیت و اطلاعات اکانت پراپ کاربر"""
    db_user = await get_db_user(db, telegram_user)
    stmt = select(PropAccount).where(PropAccount.user_id == db_user.id).order_by(PropAccount.created_at.desc())
    account = (await db.execute(stmt)).scalar_one_or_none()
    
    if not account:
        return {"has_account": False}
        
    return {
        "has_account": True,
        "account": {
            "id": str(account.id),
            "phase": account.phase,
            "status": account.status,
            "virtual_balance": float(account.virtual_balance),
            "starting_balance": float(account.starting_balance),
            "peak_balance": float(account.peak_balance),
            "target_profit_pct": float(account.target_profit_pct),
            "max_daily_drawdown_pct": float(account.max_daily_drawdown_pct),
            "max_total_drawdown_pct": float(account.max_total_drawdown_pct),
            "total_predictions": account.total_predictions,
            "winning_predictions": account.winning_predictions
        }
    }
