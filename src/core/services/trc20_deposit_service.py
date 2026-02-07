"""
TRC20 Deposit Crediting (by address)
- Exchange-style deposits: identify user by deposit_addresses.address (no memo)
"""
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    DepositAddress, Balance, Ledger, Transaction,
    TransactionType, TransactionStatus, LedgerEventType,
)

class Trc20DepositError(Exception):
    pass


async def credit_trc20_deposit_by_address(
    session: AsyncSession,
    *,
    to_address: str,
    tx_hash: str,
    amount: Decimal,
    asset: str = "USDT",
    network: str = "TRC20",
    from_address: str | None = None,
    timestamp_ms: int | None = None,
) -> dict:
    """
    Idempotent credit:
    - tx_hash unique check in transactions
    - maps to user via deposit_addresses(asset, network, address)
    - updates Balance(asset, network)
    - writes Ledger + Transaction
    """
    asset = (asset or "USDT").strip().upper()
    network = (network or "TRC20").strip().upper()
    to_address = (to_address or "").strip()

    if not to_address:
        return {"status": "ignored", "reason": "missing_to_address"}
    if not tx_hash or not str(tx_hash).strip():
        return {"status": "ignored", "reason": "missing_tx_hash"}

    if amount is None or amount <= 0:
        return {"status": "ignored", "reason": "invalid_amount"}

    # 1) tx idempotency (seen?)
    r = await session.execute(select(Transaction.id).where(Transaction.tx_hash == tx_hash))
    if r.scalar_one_or_none():
        return {"status": "ignored", "reason": "tx_already_seen"}

    # 2) find owner by deposit_addresses
    r = await session.execute(
        select(DepositAddress).where(
            DepositAddress.asset == asset,
            DepositAddress.network == network,
            DepositAddress.address == to_address,
        )
    )
    da = r.scalar_one_or_none()
    if not da:
        return {"status": "ignored", "reason": "address_not_managed"}

    user_id = da.user_id

    # 3) get/create balance
    r = await session.execute(
        select(Balance).where(
            Balance.user_id == user_id,
            Balance.asset == asset,
            Balance.network == network,
        )
    )
    bal = r.scalar_one_or_none()
    if not bal:
        bal = Balance(
            id=uuid.uuid4(),
            user_id=user_id,
            available=Decimal("0"),
            locked=Decimal("0"),
            currency=asset,
            asset=asset,
            network=network,
        )
        session.add(bal)
        await session.flush()

    available_before = Decimal(bal.available or 0)
    available_after = available_before + amount

    # 4) write Transaction + Ledger + balance
    try:
        session.add(Transaction(
            id=uuid.uuid4(),
            user_id=user_id,
            type=TransactionType.DEPOSIT,
            amount=amount,
            status=TransactionStatus.CONFIRMED,
            tx_hash=str(tx_hash),
            memo=None,
        ))

        bal.available = available_after

        desc = f"واریز {amount} {asset} ({network})"
        if from_address:
            desc += f" from {from_address[:10]}..."
        if timestamp_ms:
            try:
                dt = datetime.utcfromtimestamp(int(timestamp_ms) / 1000)
                desc += f" @ {dt.isoformat()}Z"
            except Exception:
                pass

        session.add(Ledger(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type=LedgerEventType.DEPOSIT,
            amount=amount,
            currency=asset,
            asset=asset,
            network=network,
            available_before=available_before,
            available_after=available_after,
            locked_before=bal.locked,
            locked_after=bal.locked,
            description=desc,
            idempotency_key=f"DEPOSIT:{network}:{tx_hash}",
        ))

        await session.commit()
        return {
            "status": "credited",
            "amount": float(amount),
            "to_address": to_address,
            "user_id": str(user_id),
            "new_balance": float(available_after),
        }

    except IntegrityError:
        await session.rollback()
        return {"status": "ignored", "reason": "race_duplicate"}
