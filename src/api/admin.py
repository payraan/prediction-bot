# src/api/admin.py
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from src.core.config import get_settings
from src.database.connection import async_session
from src.core.services.withdrawal_service import (
    get_needs_review_withdrawals,
    approve_withdrawal,
    cancel_withdrawal
)

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_secret: str = Header(None)):
    """Require admin secret in header"""
    if not x_admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


class WithdrawalResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    to_address: str
    status: str
    created_at: str


@router.get("/withdrawals/review", response_model=List[WithdrawalResponse])
async def list_withdrawals_review(_=Depends(require_admin)):
    """List withdrawals that need review"""
    async with async_session() as session:
        rows = await get_needs_review_withdrawals(session)
        return [
            WithdrawalResponse(
                id=str(w.id),
                user_id=str(w.user_id),
                amount=float(w.amount),
                to_address=w.to_address,
                status=w.status,
                created_at=w.created_at.isoformat()
            ) for w in rows
        ]


@router.post("/withdrawals/{withdrawal_id}/approve")
async def admin_approve(withdrawal_id: str, _=Depends(require_admin)):
    """Approve a withdrawal"""
    async with async_session() as session:
        w = await approve_withdrawal(session, uuid.UUID(withdrawal_id))
        return {"ok": True, "id": str(w.id), "status": w.status}


@router.post("/withdrawals/{withdrawal_id}/cancel")
async def admin_cancel(
    withdrawal_id: str,
    reason: str = "admin_cancel",
    _=Depends(require_admin)
):
    """Cancel a withdrawal"""
    async with async_session() as session:
        w = await cancel_withdrawal(session, uuid.UUID(withdrawal_id), reason=reason)
        return {"ok": True, "id": str(w.id), "status": w.status}
