"""
TRON / TRC20 Provider

هدف P1:
- به جای polling آدرس‌به‌آدرس (O(N))،
  انتقال‌ها را با Block Scanning می‌خوانیم (O(Blocks)).
- برای TRC20 از TronGrid Contract Events استفاده می‌کنیم و فقط Transfer event را می‌گیریم.

خروجی‌ها normalize می‌شوند:
  - hash: str
  - amount: Decimal
  - from_address: str
  - to_address: str
  - timestamp: int (ms)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from decimal import Decimal

import httpx


TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "").strip()
TRONGRID_BASE_URL = os.getenv("TRONGRID_BASE_URL", "https://api.trongrid.io").strip()


def _headers(api_key: Optional[str]) -> Optional[Dict[str, str]]:
    key = (api_key or TRONGRID_API_KEY).strip()
    return {"TRON-PRO-API-KEY": key} if key else None


def _safe_addr(s: Any) -> str:
    return (str(s) if s is not None else "").strip()


def _to_decimal_amount(raw_value: Any, decimals: int) -> Optional[Decimal]:
    if raw_value is None:
        return None
    try:
        v = Decimal(str(raw_value))
        return v / (Decimal(10) ** Decimal(int(decimals)))
    except Exception:
        return None


async def get_latest_tron_block_number(api_key: Optional[str] = None) -> int:
    """
    TronGrid endpoint: /wallet/getnowblock (POST)
    returns: block_header.raw_data.number
    """
    url = f"{TRONGRID_BASE_URL}/wallet/getnowblock"
    headers = _headers(api_key)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json={}, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    try:
        return int(data["block_header"]["raw_data"]["number"])
    except Exception:
        # fallback: if structure differs
        return int(data.get("block", {}).get("number", 0) or 0)


async def fetch_trc20_transfers_by_block(
    block_number: int,
    token_contract: str,
    limit: int = 200,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Reads TRC20 Transfer events in a specific block via TronGrid contract events.

    Endpoint (TronGrid v1):
      GET /v1/contracts/{contract}/events

    We try both snake_case and camelCase parameter names (TronGrid variants exist).
    """
    contract = (token_contract or "").strip()
    if not contract:
        return []

    url = f"{TRONGRID_BASE_URL}/v1/contracts/{contract}/events"
    headers = _headers(api_key)

    # we try camelCase first (TronGrid SDK style)
    params_candidates = [
        {
            "eventName": "Transfer",
            "onlyConfirmed": "true",
            "blockNumber": str(int(block_number)),
            "limit": str(int(limit)),
            "orderBy": "block_timestamp,asc",
        },
        # snake_case fallback (some deployments accept these)
        {
            "event_name": "Transfer",
            "only_confirmed": "true",
            "block_number": str(int(block_number)),
            "limit": str(int(limit)),
            "order_by": "block_timestamp,asc",
        },
    ]

    last_err: Optional[Exception] = None

    for params in params_candidates:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            items = data.get("data") or []
            out: List[Dict[str, Any]] = []

            for it in items:
                # event payload can be in different shapes:
                # - it["transaction_id"]
                # - it["event"] / it["result"]
                tx_hash = (
                    it.get("transaction_id")
                    or it.get("transactionId")
                    or it.get("txID")
                    or it.get("hash")
                )
                if not tx_hash:
                    continue

                result = it.get("result") or it.get("event") or {}
                # common keys: from, to, value
                from_addr = _safe_addr(result.get("from") or result.get("_from") or result.get("from_address"))
                to_addr = _safe_addr(result.get("to") or result.get("_to") or result.get("to_address"))
                raw_value = result.get("value") or result.get("_value")

                # USDT TRC20 is 6 decimals typically.
                decimals = 6
                try:
                    # sometimes token_info.decimals exists
                    token_info = it.get("token_info") or {}
                    decimals = int(token_info.get("decimals", decimals))
                except Exception:
                    decimals = 6

                amount = _to_decimal_amount(raw_value, decimals)
                if amount is None:
                    continue

                ts = it.get("block_timestamp") or it.get("timestamp") or 0
                try:
                    ts = int(ts)
                except Exception:
                    ts = 0

                out.append(
                    {
                        "hash": str(tx_hash),
                        "amount": amount,
                        "from_address": from_addr,
                        "to_address": to_addr,
                        "timestamp": ts,
                    }
                )

            return out

        except Exception as e:
            last_err = e
            continue

    if last_err:
        print(f"[TRON] fetch_trc20_transfers_by_block error: {last_err}")
    return []


# ---------------------------------------------------------------------------
# Backward-compatible: old account polling (kept as fallback / debugging)
# ---------------------------------------------------------------------------
async def fetch_incoming_trc20_transfers(
    house_address: str,
    token_contract: str,
    limit: int = 50,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Old method (O(N) if used per-address): account TRC20 transfers.

    Keeping for fallback/debug only.
    """
    address = (house_address or "").strip()
    contract = (token_contract or "").strip()
    if not address or not contract:
        return []

    headers = _headers(api_key)

    url = f"{TRONGRID_BASE_URL}/v1/accounts/{address}/transactions/trc20"
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
            tx_hash = it.get("transaction_id") or it.get("transactionId") or it.get("txID") or it.get("hash")
            if not tx_hash:
                continue

            to_addr = _safe_addr(it.get("to") or it.get("to_address"))
            if to_addr and to_addr.upper() != address.upper():
                continue

            from_addr = _safe_addr(it.get("from") or it.get("from_address"))
            raw_value = it.get("value")
            if raw_value is None:
                continue

            token_info = it.get("token_info") or {}
            try:
                decimals = int(token_info.get("decimals", 6))
            except Exception:
                decimals = 6

            amount = _to_decimal_amount(raw_value, decimals)
            if amount is None:
                continue

            ts = it.get("block_timestamp") or it.get("timestamp") or 0
            try:
                ts = int(ts)
            except Exception:
                ts = 0

            out.append(
                {
                    "hash": str(tx_hash),
                    "amount": amount,
                    "from_address": from_addr,
                    "to_address": to_addr,
                    "timestamp": ts,
                }
            )

        return out

    except httpx.HTTPError as e:
        print(f"HTTP error fetching TRC20 transfers: {e}")
        return []
    except Exception as e:
        print(f"Error fetching TRC20 transfers: {e}")
        return []
