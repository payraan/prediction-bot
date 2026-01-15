"""
Deposit Service
سرویس مدیریت واریز TON - نسخه امن نهایی
"""

import uuid
import secrets
import string
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    DepositRequest, Transaction, TransactionType, TransactionStatus,
    Balance, Ledger, LedgerEventType, User
)
from src.core.config import get_settings

settings = get_settings()

MEMO_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
AMOUNT_TOLERANCE = Decimal("0.01")


def generate_deposit_memo(length: int = 8) -> str:
    token = "".join(secrets.choice(MEMO_ALPHABET) for _ in range(length))
    return f"DP-{token}"


async def create_deposit_request(
    session: AsyncSession,
    telegram_id: int,
    expected_amount: Decimal = None,
    expires_minutes: int = 30,
) -> dict:
    
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise ValueError("کاربر یافت نشد")
    
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    
    for _ in range(5):
        memo = generate_deposit_memo()
        
        deposit_request = DepositRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            memo=memo,
            expected_amount=expected_amount,
            status=TransactionStatus.PENDING,
            expires_at=expires_at,
        )
        session.add(deposit_request)
        
        try:
            await session.commit()
            
            return {
                "memo": memo,
                "to_address": settings.ton_house_wallet_address,
                "expected_amount": float(expected_amount) if expected_amount else None,
                "expires_at": expires_at.isoformat(),
                "expires_minutes": expires_minutes,
            }
        except IntegrityError:
            await session.rollback()
            continue
    
    raise RuntimeError("خطا در ساخت memo یونیک")


async def get_pending_deposit(
    session: AsyncSession,
    telegram_id: int,
) -> dict | None:
    
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    result = await session.execute(
        select(DepositRequest).where(
            DepositRequest.user_id == user.id,
            DepositRequest.status == TransactionStatus.PENDING,
            DepositRequest.expires_at > datetime.utcnow()
        ).order_by(DepositRequest.created_at.desc())
    )
    deposit_request = result.scalar_one_or_none()
    
    if not deposit_request:
        return None
    
    return {
        "memo": deposit_request.memo,
        "to_address": settings.ton_house_wallet_address,
        "expected_amount": float(deposit_request.expected_amount) if deposit_request.expected_amount else None,
        "expires_at": deposit_request.expires_at.isoformat(),
    }


async def credit_deposit(
    session: AsyncSession,
    memo: str,
    tx_hash: str,
    amount: Decimal,
) -> dict:
    """
    ثبت واریز تایید شده (atomic + idempotent)
    """
    
    # چک مبلغ مثبت
    if amount <= 0:
        return {"status": "ignored", "reason": "invalid_amount"}
    
    # پیدا کردن درخواست واریز
    result = await session.execute(
        select(DepositRequest).where(DepositRequest.memo == memo)
    )
    deposit_request = result.scalar_one_or_none()
    
    if not deposit_request:
        return {"status": "ignored", "reason": "memo_not_found"}
    
    if deposit_request.status != TransactionStatus.PENDING:
        return {"status": "ignored", "reason": "already_processed"}
    
    # چک expiry
    if deposit_request.expires_at and deposit_request.expires_at < datetime.utcnow():
        return {"status": "ignored", "reason": "expired"}
    
    # چک مبلغ
    if deposit_request.expected_amount is not None:
        expected = Decimal(str(deposit_request.expected_amount))
        if abs(amount - expected) > AMOUNT_TOLERANCE:
            return {
                "status": "ignored", 
                "reason": "amount_mismatch",
                "expected": float(expected),
                "received": float(amount),
            }
    
    # چک tx_hash تکراری
    result = await session.execute(
        select(Transaction.id).where(Transaction.tx_hash == tx_hash)
    )
    if result.scalar_one_or_none():
        return {"status": "ignored", "reason": "tx_already_seen"}
    
    user_id = deposit_request.user_id
    
    # گرفتن یا ساختن Balance
    result = await session.execute(
        select(Balance).where(Balance.user_id == user_id)
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        balance = Balance(
            id=uuid.uuid4(),
            user_id=user_id,
            available=Decimal("0"),
            locked=Decimal("0"),
            currency="TON"
        )
        session.add(balance)
        await session.flush()
    
    available_before = balance.available
    available_after = available_before + amount
    
    idempotency_key = f"DEPOSIT:{tx_hash}"
    
    try:
        session.add(Transaction(
            id=uuid.uuid4(),
            user_id=user_id,
            type=TransactionType.DEPOSIT,
            amount=amount,
            status=TransactionStatus.CONFIRMED,
            tx_hash=tx_hash,
            memo=memo,
        ))
        
        balance.available = available_after
        
        session.add(Ledger(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type=LedgerEventType.DEPOSIT,
            amount=amount,
            currency="TON",
            available_before=available_before,
            available_after=available_after,
            locked_before=balance.locked,
            locked_after=balance.locked,
            description=f"واریز {amount} TON",
            idempotency_key=idempotency_key,
        ))
        
        deposit_request.status = TransactionStatus.CONFIRMED
        
        await session.commit()
        
        return {
            "status": "credited",
            "amount": float(amount),
            "memo": memo,
            "new_balance": float(available_after),
        }
        
    except IntegrityError:
        await session.rollback()
        return {"status": "ignored", "reason": "race_duplicate"}
