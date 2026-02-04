# src/core/services/reconciliation.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.database.models import Balance, Ledger, LedgerEventType
from src.core.services.alerts import alert_admin


async def reconcile(session: AsyncSession):
    """
    Daily reconciliation check
    
    Checks:
    1. Total user balances (available + locked)
    2. Total house fees collected
    3. Sanity checks for negative balances
    """
    
    # Total user balances
    bal_sum = await session.execute(
        select(func.coalesce(func.sum(Balance.available + Balance.locked), 0))
    )
    total_bal = Decimal(str(bal_sum.scalar_one()))
    
    # Total house fees
    fee_sum = await session.execute(
        select(func.coalesce(func.sum(Ledger.amount), 0))
        .where(Ledger.event_type == LedgerEventType.HOUSE_FEE)
    )
    total_fees = Decimal(str(fee_sum.scalar_one()))
    
    # Sanity checks
    alerts = []
    
    if total_bal < 0:
        alerts.append(f"🚨 CRITICAL: Total user balance is NEGATIVE ({total_bal} TON)")
    
    if total_fees < 0:
        alerts.append(f"⚠️ WARNING: Total house fees is NEGATIVE ({total_fees} TON)")
    
    # Send alerts
    for alert_msg in alerts:
        await alert_admin(alert_msg)
    
    result = {
        "total_user_balance": str(total_bal),
        "total_house_fees": str(total_fees),
        "alerts": alerts,
        "status": "critical" if alerts else "ok"
    }
    
    return result
