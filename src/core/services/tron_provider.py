"""
TRON / TRC20 Provider
- گرفتن تراکنش‌های ورودی TRC20 (مثل USDT) به آدرس خزانه
- NOTE: TRC20 معمولاً memo ندارد؛ بنابراین memo=None خواهد بود.
"""

from __future__ import annotations

import os
import httpx
from typing import Any, Dict, List, Optional
from decimal import Decimal


TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "").strip()


async def fetch_incoming_trc20_transfers(
    house_address: str,
    token_contract: str,
    limit: int = 50,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return list of normalized incoming TRC20 transfers.

    Each item includes:
      - hash: str
      - amount: Decimal
      - memo: Optional[str]  (TRC20 usually None)
      - from_address: str
      - timestamp: int (ms)
    """
    address = (house_address or "").strip()
    contract = (token_contract or "").strip()
    if not address or not contract:
        return []

    key = (api_key or TRONGRID_API_KEY).strip()
    headers = {"TRON-PRO-API-KEY": key} if key else None

    # TronGrid v1 endpoint: account TRC20 transfers
    url = f"https://api.trongrid.io/v1/accounts/{address}/transactions/trc20"

    params = {
        "only_confirmed": "true",
        "limit": str(int(limit)),
        "contract_address": contract,
        "order_by": "block_timestamp,desc",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("data") or []
        out: List[Dict[str, Any]] = []

        for it in items:
            # Defensive parsing: TronGrid fields can vary slightly
            tx_hash = it.get("transaction_id") or it.get("transactionId") or it.get("txID") or it.get("hash")
            if not tx_hash:
                continue

            to_addr = (it.get("to") or it.get("to_address") or "").strip()
            if to_addr and to_addr.upper() != address.upper():
                # sometimes endpoint returns both directions; keep only incoming to house
                continue

            from_addr = (it.get("from") or it.get("from_address") or "").strip()

            # Amount parsing:
            # - 'value' may be string
            # - decimals may be in token_info.decimals
            raw_value = it.get("value")
            if raw_value is None:
                continue

            token_info = it.get("token_info") or {}
            try:
                decimals = int(token_info.get("decimals", 6))
            except Exception:
                decimals = 6

            try:
                # value may already be a decimal string in "human" units on some providers,
                # but TronGrid typically returns integer-like string of base units.
                v = Decimal(str(raw_value))
                amount = v / (Decimal(10) ** Decimal(decimals))
            except Exception:
                continue

            ts = it.get("block_timestamp") or it.get("timestamp") or 0
            try:
                ts = int(ts)
            except Exception:
                ts = 0

            out.append({
                "hash": str(tx_hash),
                "amount": amount,
                "memo": None,
                "from_address": from_addr,
                "to_address": to_addr,
                "timestamp": ts,
            })

        return out

    except httpx.HTTPError as e:
        print(f"HTTP error fetching TRC20 transfers: {e}")
        return []
    except Exception as e:
        print(f"Error fetching TRC20 transfers: {e}")
        return []
