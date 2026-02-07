"""
Deposit Observer
اسکن تراکنش‌های ورودی و تایید واریزها
"""

import asyncio
import os
from decimal import Decimal

from src.database.connection import async_session
from src.core.config import get_settings, TRC20_TOKEN_CONTRACTS
from src.core.services.deposit_service import credit_deposit
from src.core.services.trc20_deposit_service import credit_trc20_deposit_by_address
from src.core.services.ton_provider import fetch_incoming_transactions
from src.core.services.tron_provider import fetch_incoming_trc20_transfers
from src.core.services.alerts import alert_admin

settings = get_settings()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


async def process_deposits(asset: str = 'TON', network: str = 'TON'):
    """
    یک سیکل اسکن تراکنش‌ها
    """

    a = (asset or 'TON').strip().upper()
    n = (network or 'TON').strip().upper()

    if a == 'TON' and n == 'TON':
        pass
    elif a == 'USDT' and n == 'TRC20':
        pass
    else:
        raise NotImplementedError(f'Deposit observer for {a}-{n} is not implemented yet')

    limit = _env_int("DEPOSIT_OBSERVER_LIMIT", 50)

    transactions = []

    if a == "TON" and n == "TON":
        house_address = settings.ton_house_wallet_address
        if not house_address:
            raise RuntimeError("TON_HOUSE_WALLET_ADDRESS is not set")
        transactions = await fetch_incoming_transactions(house_address, limit=limit)

    elif a == "USDT" and n == "TRC20":
        token_contract = TRC20_TOKEN_CONTRACTS.get((a, n))
        if not token_contract:
            raise RuntimeError(f"missing_trc20_contract for {a}-{n}")

        # per-user addresses
        from sqlalchemy import select
        from src.database.models import DepositAddress

        async with async_session() as session:
            rows = (await session.execute(
                select(DepositAddress).where(
                    DepositAddress.asset == a,
                    DepositAddress.network == n,
                )
            )).scalars().all()

        # fetch tx per address (small batch)
        for da in rows:
            txs = await fetch_incoming_trc20_transfers(
                house_address=da.address,
                token_contract=token_contract,
                limit=limit,
            )
            transactions.extend(txs)

    else:
        raise NotImplementedError(f"Deposit observer for {a}-{n} is not implemented yet")

    processed = 0
    credited = 0

    async with async_session() as session:
        for tx in transactions:
            # TON مسیر memo-based
            if a == "TON" and n == "TON":
                memo = tx.get("memo")
                if not memo or not memo.startswith("DP-"):
                    continue
                processed += 1
                result = await credit_deposit(
                    session,
                    memo=memo,
                    tx_hash=tx["hash"],
                    amount=tx["amount"],
                )

            # TRC20 مسیر address-based (بدون memo)
            elif a == "USDT" and n == "TRC20":
                processed += 1
                result = await credit_trc20_deposit_by_address(
                    session,
                    to_address=tx.get("to_address") or "",
                    tx_hash=tx["hash"],
                    amount=tx["amount"],
                    asset=a,
                    network=n,
                    from_address=tx.get("from_address"),
                    timestamp_ms=tx.get("timestamp"),
                )
            else:
                continue

            if result["status"] == "credited":
                credited += 1
                print(f"💰 واریز تایید شد: {tx['amount']} | hash: {tx['hash']}")
            elif result["status"] == "ignored" and result.get("reason") not in ["tx_already_seen", "already_processed"]:
                print(f"⚠️ واریز نادیده گرفته شد: {result.get('reason')} | hash: {tx['hash']}")

    return {"processed": processed, "credited": credited}

async def run_deposit_observer(interval_seconds: int = 15):
    interval_seconds = _env_int('DEPOSIT_OBSERVER_INTERVAL_SECONDS', interval_seconds)

    observer_asset = os.getenv('DEPOSIT_OBSERVER_ASSET', 'TON').strip().upper()
    observer_network = os.getenv('DEPOSIT_OBSERVER_NETWORK', 'TON').strip().upper()

    """
    حلقه اصلی Observer
    """
    
    print("=" * 50)
    print("💰 Deposit Observer شروع شد")
    print(f"   آدرس خزانه: {settings.ton_house_wallet_address[:20]}...")
    print(f"   دارایی/شبکه: {observer_asset}/{observer_network}")
    print(f"   فاصله اسکن: {interval_seconds} ثانیه")
    print("=" * 50)
    
    while True:
        try:
            result = await process_deposits(asset=observer_asset, network=observer_network)
            
            if result["credited"] > 0:
                print(f"✅ این سیکل: {result['credited']} واریز تایید شد")
                
        except Exception as e:
            print(f"❌ خطا در Observer: {e}")
            await alert_admin(f"🚨 Deposit Observer Error: {e}")
       
        await asyncio.sleep(interval_seconds)


async def run_single_scan():
    """
    اجرای یک اسکن (برای تست)
    """
    print("🔍 اسکن تراکنش‌ها...")
    result = await process_deposits(asset=os.getenv('DEPOSIT_OBSERVER_ASSET','TON'), network=os.getenv('DEPOSIT_OBSERVER_NETWORK','TON'))
    print(f"نتیجه: {result}")
    return result


# برای اجرا به صورت standalone
if __name__ == "__main__":
    asyncio.run(run_deposit_observer())
