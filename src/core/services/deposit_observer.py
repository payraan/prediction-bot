"""
Deposit Observer
اسکن تراکنش‌های ورودی و تایید واریزها
"""

import asyncio
import os
from decimal import Decimal

from src.database.connection import async_session
from src.core.config import get_settings
from src.core.services.deposit_service import credit_deposit
from src.core.services.ton_provider import fetch_incoming_transactions
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


async def process_deposits():
    """
    یک سیکل اسکن تراکنش‌ها
    """

    house_address = settings.ton_house_wallet_address
    if not house_address:
        raise RuntimeError("TON_HOUSE_WALLET_ADDRESS is not set")

    limit = _env_int("DEPOSIT_OBSERVER_LIMIT", 50)

    # گرفتن تراکنش‌های اخیر
    transactions = await fetch_incoming_transactions(house_address, limit=limit)

    processed = 0
    credited = 0

    # یک session برای کل batch (بهینه‌تر)
    async with async_session() as session:
        for tx in transactions:
            memo = tx.get("memo")

            # فقط تراکنش‌هایی که memo دارن و با DP- شروع میشن
            if not memo or not memo.startswith("DP-"):
                continue

            processed += 1

            result = await credit_deposit(
                session,
                memo=memo,
                tx_hash=tx["hash"],
                amount=tx["amount"],
            )

            if result["status"] == "credited":
                credited += 1
                print(f"💰 واریز تایید شد: {tx['amount']} TON | memo: {memo}")
            elif result["status"] == "ignored" and result.get("reason") not in ["tx_already_seen", "already_processed"]:
                print(f"⚠️ واریز نادیده گرفته شد: {result.get('reason')} | memo: {memo}")

    return {"processed": processed, "credited": credited}

async def run_deposit_observer(interval_seconds: int = 15):
    interval_seconds = _env_int('DEPOSIT_OBSERVER_INTERVAL_SECONDS', interval_seconds)

    """
    حلقه اصلی Observer
    """
    
    print("=" * 50)
    print("💰 Deposit Observer شروع شد")
    print(f"   آدرس خزانه: {settings.ton_house_wallet_address[:20]}...")
    print(f"   شبکه: {settings.ton_network}")
    print(f"   فاصله اسکن: {interval_seconds} ثانیه")
    print("=" * 50)
    
    while True:
        try:
            result = await process_deposits()
            
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
    result = await process_deposits()
    print(f"نتیجه: {result}")
    return result


# برای اجرا به صورت standalone
if __name__ == "__main__":
    asyncio.run(run_deposit_observer())
