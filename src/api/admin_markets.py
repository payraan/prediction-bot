import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import async_session
from src.api.admin import require_admin
from src.core.services.local_market_service import (
    create_local_market, propose_resolution, finalize_market
)

router = APIRouter(prefix="/api/admin/markets", tags=["Admin Local Markets"])

async def get_db():
    async with async_session() as session:
        yield session

class CreateMarketRequest(BaseModel):
    title: str
    description: str = None
    category: str = "GENERAL"
    closes_at: datetime

class ResolveMarketRequest(BaseModel):
    outcome: str # "YES" or "NO"
    evidence_url: str = None

@router.post("/create")
async def api_create_market(req: CreateMarketRequest, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    """ساخت بازار بومی جدید توسط ادمین"""
    market = await create_local_market(
        session=db,
        title=req.title,
        closes_at=req.closes_at,
        description=req.description,
        category=req.category,
        admin_id=None
    )
    return {"status": "success", "market_id": market.id}

@router.post("/{market_id}/resolve")
async def api_propose_resolution(market_id: uuid.UUID, req: ResolveMarketRequest, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    """اعلام نتیجه بازار (شروع مهلت ۲۴ ساعته اعتراض)"""
    try:
        resolution = await propose_resolution(db, market_id, req.outcome, None, req.evidence_url)
        return {"status": "success", "resolution_id": resolution.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{market_id}/finalize")
async def api_finalize_market(market_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    """تسویه نهایی بازار و واریز سودها (Idempotent)"""
    try:
        result = await finalize_market(db, market_id)
        return {"status": "success", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
