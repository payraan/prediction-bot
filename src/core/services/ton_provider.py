"""
TON Provider
لایه ارتباط با بلاکچین TON
"""

import httpx
from decimal import Decimal
from src.core.config import get_settings

settings = get_settings()


async def fetch_incoming_transactions(address: str, limit: int = 50) -> list[dict]:
    """
    گرفتن تراکنش‌های ورودی به یک آدرس
    خروجی: لیست از {hash, amount, memo, from_address}
    """
    
    # انتخاب endpoint بر اساس شبکه
    if settings.ton_network == "mainnet":
        base_url = "https://toncenter.com/api/v2"
    else:
        base_url = "https://testnet.toncenter.com/api/v2"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{base_url}/getTransactions",
                params={
                    "address": address,
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
        
        if not data.get("ok"):
            print(f"TON API error: {data}")
            return []
        
        transactions = []
        
        for tx in data.get("result", []):
            # فقط تراکنش‌های ورودی (in_msg با value > 0)
            in_msg = tx.get("in_msg", {})
            
            # مقدار به nanoTON هست، تبدیل به TON
            value_nano = int(in_msg.get("value", 0))
            if value_nano <= 0:
                continue
            
            amount = Decimal(value_nano) / Decimal("1000000000")  # nano to TON
            
            # گرفتن memo (comment)
            memo = None
            msg_data = in_msg.get("msg_data", {})
            if msg_data.get("@type") == "msg.dataText":
                memo = msg_data.get("text", "")
            
            # ساخت hash یونیک از transaction_id
            tx_hash = f"{tx.get('transaction_id', {}).get('lt', '')}_{tx.get('transaction_id', {}).get('hash', '')}"
            
            transactions.append({
                "hash": tx_hash,
                "amount": amount,
                "memo": memo,
                "from_address": in_msg.get("source", ""),
                "timestamp": tx.get("utime", 0),
            })
        
        return transactions
        
    except httpx.HTTPError as e:
        print(f"HTTP error fetching TON transactions: {e}")
        return []
    except Exception as e:
        print(f"Error fetching TON transactions: {e}")
        return []


async def test_connection() -> bool:
    """
    تست اتصال به TON API
    """
    if settings.ton_network == "mainnet":
        base_url = "https://toncenter.com/api/v2"
    else:
        base_url = "https://testnet.toncenter.com/api/v2"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/getMasterchainInfo")
            response.raise_for_status()
            data = response.json()
            return data.get("ok", False)
    except Exception as e:
        print(f"TON connection test failed: {e}")
        return False
