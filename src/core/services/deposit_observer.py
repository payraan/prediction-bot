"""
Deposit Observer
اسکن تراکنش‌های ورودی و تایید واریزها
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from src.database.connection import async_session
from src.database.models import DepositAddress
from src.core.config import get_settings, TRC20_TOKEN_CONTRACTS, EVM_TOKEN_CONTRACTS
from src.core.services.deposit_service import credit_deposit
from src.core.services.trc20_deposit_service import credit_trc20_deposit_by_address
from src.core.services.ton_provider import fetch_incoming_transactions
from src.core.services.tron_provider import (
    get_latest_tron_block_number,
    fetch_trc20_transfers_by_block,
)
from src.core.services.evm_provider import fetch_incoming_evm_transfers
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


_TRON_CURSOR_FILE = Path(os.getenv("TRON_OBSERVER_CURSOR_FILE", ".tron_observer_cursor.json"))


def _load_tron_cursor() -> Optional[int]:
    try:
        if _TRON_CURSOR_FILE.exists():
            data = json.loads(_TRON_CURSOR_FILE.read_text(encoding="utf-8"))
            v = data.get("last_scanned_block")
            return int(v) if v is not None else None
    except Exception:
        return None
    return None


def _save_tron_cursor(block_number: int) -> None:
    try:
        _TRON_CURSOR_FILE.write_text(
            json.dumps({"last_scanned_block": int(block_number)}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        # best-effort; idempotency protects us anyway
        pass


def _norm_addr(addr: str) -> str:
    return (addr or "").strip().lower()


def _get_trc20_contract(asset: str, network: str) -> Optional[str]:
    """
    Robust lookup for TRC20 contracts.
    Supports configs shaped like:
      TRC20_TOKEN_CONTRACTS[("USDT","TRC20")] = "..."
      TRC20_TOKEN_CONTRACTS[("USDT","TRON")]  = "..."
      TRC20_TOKEN_CONTRACTS["USDT"]           = "..."
    """
    a = (asset or "").strip().upper()
    n = (network or "").strip().upper()

    for key in (
        (a, n),
        (a, "TRC20"),
        (a, "TRON"),
        a,
    ):
        try:
            v = TRC20_TOKEN_CONTRACTS.get(key)  # type: ignore[attr-defined]
            if v:
                return str(v).strip()
        except Exception:
            continue
    return None


async def process_deposits(asset: str = "TON", network: str = "TON"):
    """
    یک سیکل اسکن تراکنش‌ها
    """
    a = (asset or "TON").strip().upper()
    n = (network or "TON").strip().upper()

    if a == "TON" and n == "TON":
        pass
    elif a == "USDT" and n in ("TRC20", "ERC20", "BEP20"):
        pass
    else:
        raise NotImplementedError(f"Deposit observer for {a}-{n} is not implemented yet")

    limit = _env_int("DEPOSIT_OBSERVER_LIMIT", 50)

    processed = 0
    credited = 0

    # ----------------------------
    # 1) TON (memo-based)
    # ----------------------------
    if a == "TON" and n == "TON":
        house_address = settings.ton_house_wallet_address
        if not house_address:
            raise RuntimeError("TON_HOUSE_WALLET_ADDRESS is not set")

        transactions = await fetch_incoming_transactions(house_address, limit=limit)

        async with async_session() as session:
            for tx in transactions:
                memo = tx.get("memo")
                if not memo or not str(memo).startswith("DP-"):
                    continue

                processed += 1
                result = await credit_deposit(
                    session,
                    memo=memo,
                    tx_hash=tx["hash"],
                    amount=tx["amount"],
                )

                if result.get("status") == "credited":
                    credited += 1
                    print(f"💰 واریز تایید شد: {tx['amount']} | hash: {tx['hash']}")
                elif result.get("status") == "ignored" and result.get("reason") not in (
                    "tx_already_seen",
                    "already_processed",
                ):
                    print(f"⚠️ واریز نادیده گرفته شد: {result.get('reason')} | hash: {tx['hash']}")

        return {"processed": processed, "credited": credited}

    # ----------------------------
    # 2) USDT/TRC20 (block scanning + cursor)
    # ----------------------------
    if a == "USDT" and n == "TRC20":
        token_contract = _get_trc20_contract(a, n)
        if not token_contract:
            raise RuntimeError(f"missing_trc20_contract for {a}-{n} in TRC20_TOKEN_CONTRACTS")

        confirmations = _env_int("TRON_OBSERVER_CONFIRMATIONS", 20)

        # load deposit addresses once
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(DepositAddress).where(
                        DepositAddress.asset == a,
                        DepositAddress.network == n,
                    )
                )
            ).scalars().all()

            addr_set = {_norm_addr(da.address) for da in rows if da.address}

            if not addr_set:
                return {"processed": 0, "credited": 0}

            cursor = _load_tron_cursor()
            head = await get_latest_tron_block_number()
            safe_head = max(head - confirmations, 0)

            if cursor is None:
                # start slightly behind to avoid missing anything on first run
                cursor = max(safe_head - 200, 0)

            # scan forward
            for bn in range(cursor + 1, safe_head + 1):
                txs = await fetch_trc20_transfers_by_block(
                    block_number=bn,
                    token_contract=token_contract,
                )

                for tx in txs:
                    to_addr = _norm_addr(tx.get("to_address") or "")
                    if not to_addr or to_addr not in addr_set:
                        continue

                    processed += 1
                    result = await credit_trc20_deposit(
                        session=session,
                        to_address=tx.get("to_address") or "",
                        tx_hash=tx["hash"],
                        amount=tx["amount"],
                        asset=a,
                        network=n,
                        from_address=tx.get("from_address"),
                        timestamp_ms=tx.get("timestamp"),
                    )

                    if result.get("status") == "credited":
                        credited += 1
                        print(f"💰 واریز تایید شد: {tx['amount']} | hash: {tx['hash']}")
                    elif result.get("status") == "ignored" and result.get("reason") not in (
                        "tx_already_seen",
                        "already_processed",
                    ):
                        print(f"⚠️ واریز نادیده گرفته شد: {result.get('reason')} | hash: {tx['hash']}")

                _save_tron_cursor(bn)

        return {"processed": processed, "credited": credited}

    # ----------------------------
    # 3) USDT/ERC20 or USDT/BEP20 (batch fetch by address list)
    # ----------------------------
    if a == "USDT" and n in ("ERC20", "BEP20"):
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(DepositAddress).where(
                        DepositAddress.asset == a,
                        DepositAddress.network == n,
                    )
                )
            ).scalars().all()

            if not rows:
                return {"processed": 0, "credited": 0}

            addr_list = [da.address for da in rows if da.address]
            transactions = await fetch_incoming_evm_transfers(
                addresses=addr_list,
                network=n,
                asset=a,
            )

            for tx in transactions:
                processed += 1
                result = await credit_trc20_deposit(
                    session=session,
                    to_address=tx.get("to_address") or "",
                    tx_hash=tx["hash"],
                    amount=tx["amount"],
                    asset=a,
                    network=n,
                    from_address=tx.get("from_address"),
                    timestamp_ms=tx.get("timestamp"),
                )

                if result.get("status") == "credited":
                    credited += 1
                    print(f"💰 واریز تایید شد: {tx['amount']} | hash: {tx['hash']}")
                elif result.get("status") == "ignored" and result.get("reason") not in (
                    "tx_already_seen",
                    "already_processed",
                ):
                    print(f"⚠️ واریز نادیده گرفته شد: {result.get('reason')} | hash: {tx['hash']}")

        return {"processed": processed, "credited": credited}

    raise NotImplementedError(f"Deposit observer for {a}-{n} is not implemented yet")


async def run_deposit_observer(interval_seconds: int = 15):
    interval_seconds = _env_int("DEPOSIT_OBSERVER_INTERVAL_SECONDS", interval_seconds)

    networks_to_scan = [
        ("TON", "TON"),
        ("USDT", "TRC20"),
        ("USDT", "ERC20"),
        ("USDT", "BEP20"),
    ]

    print("=" * 50)
    print("💰 Deposit Observer شروع شد (multi-network)")
    net_names = [f"{a}/{n}" for a, n in networks_to_scan]
    print(f"   شبکه‌ها: {net_names}")
    print(f"   فاصله اسکن: {interval_seconds} ثانیه")
    print("=" * 50)

    while True:
        for asset, network in networks_to_scan:
            try:
                result = await process_deposits(asset=asset, network=network)
                if result.get("credited", 0) > 0:
                    print(f"✅ {asset}/{network}: {result['credited']} واریز تایید شد")
            except Exception as e:
                print(f"❌ خطا در Observer ({asset}/{network}): {e}")
                await alert_admin(f"🚨 Deposit Observer Error ({asset}/{network}): {e}")

        await asyncio.sleep(interval_seconds)


async def run_single_scan():
    """
    اجرای یک اسکن (برای تست)
    """
    print("🔍 اسکن تراکنش‌ها...")
    result = await process_deposits(
        asset=os.getenv("DEPOSIT_OBSERVER_ASSET", "TON"),
        network=os.getenv("DEPOSIT_OBSERVER_NETWORK", "TON"),
    )
    print(f"نتیجه: {result}")
    return result


if __name__ == "__main__":
    asyncio.run(run_deposit_observer())
