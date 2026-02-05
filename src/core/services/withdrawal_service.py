"""
Withdrawal Service
سرویس برداشت TON
"""

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    User, Balance, Withdrawal, Ledger,
    WithdrawalStatus, LedgerEventType
)
from src.core.config import get_settings

settings = get_settings()

# حد برداشت خودکار (بالاتر نیاز به تأیید ادمین)
AUTO_WITHDRAWAL_LIMIT = Decimal("50")  # TON
MIN_WITHDRAWAL_AMOUNT = Decimal("1")   # حداقل برداشت


class WithdrawalError(Exception):
    """خطای برداشت"""
    pass


async def request_withdrawal(
    session: AsyncSession,
    telegram_id: int,
    amount: Decimal,
    to_address: str,
    network: str | None = None
) -> Withdrawal:
    """
    ثبت درخواست برداشت
    """
    
    # ۱. پیدا کردن کاربر
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise WithdrawalError("کاربر پیدا نشد")
    
    # ۲. چک حداقل مبلغ
    if amount < MIN_WITHDRAWAL_AMOUNT:
        raise WithdrawalError(f"حداقل برداشت {MIN_WITHDRAWAL_AMOUNT} TON است")
    
    # ۳. چک موجودی
    balance_result = await session.execute(
        select(Balance).where(Balance.user_id == user.id)
    )
    balance = balance_result.scalar_one_or_none()
    
    if not balance or balance.available < amount:
        raise WithdrawalError("موجودی کافی نیست")
    
    # ۴. چک آدرس معتبر
    if not to_address or len(to_address) < 20:
        raise WithdrawalError("آدرس کیف پول نامعتبر است")


    resolved_network = (network or settings.default_network).strip().upper()
    
    # ۵. ذخیره وضعیت قبلی برای Ledger
    available_before = balance.available
    locked_before = balance.locked
    
    # ۶. قفل کردن مبلغ (از available به locked)
    balance.available -= amount
    balance.locked += amount
    
    # ۷. تعیین وضعیت اولیه
    if amount >= AUTO_WITHDRAWAL_LIMIT:
        status = WithdrawalStatus.NEEDS_REVIEW
    else:
        status = WithdrawalStatus.PENDING
    
    # ۸. ساخت درخواست برداشت
    withdrawal = Withdrawal(
        id=uuid.uuid4(),
        user_id=user.id,
        amount=amount,
        currency=settings.default_asset,
        asset=settings.default_asset,
        network=resolved_network,
        to_address=to_address,
        status=status
    )
    session.add(withdrawal)
    
    # ۹. ثبت در Ledger
    ledger_entry = Ledger(
        id=uuid.uuid4(),
        user_id=user.id,
        event_type=LedgerEventType.WITHDRAWAL,
        amount=amount,
        currency=settings.default_asset,
        asset=settings.default_asset,
        network=resolved_network,
        available_before=available_before,
        available_after=balance.available,
        locked_before=locked_before,
        locked_after=balance.locked,
        description=f"درخواست برداشت {amount} {settings.default_asset} به {to_address[:20]}...",
        idempotency_key=f"WITHDRAWAL_REQUEST:{withdrawal.id}"
    )
    session.add(ledger_entry)
    
    await session.commit()
    
    return withdrawal


async def get_user_withdrawals(
    session: AsyncSession,
    telegram_id: int,
    limit: int = 20
) -> list:
    """
    گرفتن تاریخچه برداشت‌های کاربر
    """
    
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return []
    
    result = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.user_id == user.id)
        .order_by(Withdrawal.created_at.desc())
        .limit(limit)
    )
    
    return result.scalars().all()


async def get_pending_withdrawals(session: AsyncSession) -> list:
    """
    گرفتن برداشت‌های در انتظار پردازش (برای worker)
    """
    result = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.status == WithdrawalStatus.PENDING)
        .order_by(Withdrawal.created_at.asc())
        .limit(10)
    )
    return result.scalars().all()


async def get_needs_review_withdrawals(session: AsyncSession) -> list:
    """
    گرفتن برداشت‌های نیازمند تأیید ادمین
    """
    result = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.status == WithdrawalStatus.NEEDS_REVIEW)
        .order_by(Withdrawal.created_at.asc())
    )
    return result.scalars().all()


async def approve_withdrawal(
    session: AsyncSession,
    withdrawal_id: uuid.UUID,
    admin_note: str = None
) -> Withdrawal:
    """
    تأیید برداشت توسط ادمین
    """
    result = await session.execute(
        select(Withdrawal).where(Withdrawal.id == withdrawal_id)
    )
    withdrawal = result.scalar_one_or_none()
    
    if not withdrawal:
        raise WithdrawalError("برداشت پیدا نشد")
    
    if withdrawal.status != WithdrawalStatus.NEEDS_REVIEW:
        raise WithdrawalError("این برداشت قابل تأیید نیست")
    
    withdrawal.status = WithdrawalStatus.APPROVED
    withdrawal.admin_note = admin_note
    
    await session.commit()
    return withdrawal


async def cancel_withdrawal(
    session: AsyncSession,
    withdrawal_id: uuid.UUID,
    reason: str = None
) -> Withdrawal:
    """
    لغو برداشت و برگشت موجودی
    """
    result = await session.execute(
        select(Withdrawal).where(Withdrawal.id == withdrawal_id)
    )
    withdrawal = result.scalar_one_or_none()
    
    if not withdrawal:
        raise WithdrawalError("برداشت پیدا نشد")
    
    if withdrawal.status in [WithdrawalStatus.SENT, WithdrawalStatus.CONFIRMED]:
        raise WithdrawalError("این برداشت قابل لغو نیست")
    
    # برگشت موجودی
    balance_result = await session.execute(
        select(Balance).where(Balance.user_id == withdrawal.user_id)
    )
    balance = balance_result.scalar_one()
    
    balance.locked -= withdrawal.amount
    balance.available += withdrawal.amount
    
    withdrawal.status = WithdrawalStatus.CANCELLED
    withdrawal.admin_note = reason
    
    # ثبت در Ledger
    ledger_entry = Ledger(
        id=uuid.uuid4(),
        user_id=withdrawal.user_id,
        event_type=LedgerEventType.REFUND,
        amount=withdrawal.amount,
        currency=settings.default_asset,
        asset=settings.default_asset,
        network=resolved_network,
        description=f"لغو برداشت: {reason or 'بدون دلیل'}",
        idempotency_key=f"WITHDRAWAL_CANCEL:{withdrawal.id}"
    )
    session.add(ledger_entry)
    
    await session.commit()
    return withdrawal
