"""
Price Service
گرفتن قیمت از Binance
"""

import httpx
from decimal import Decimal
from typing import Optional

BINANCE_API = "https://api.binance.com/api/v3"


async def get_current_price(symbol: str = "BTCUSDT") -> Optional[Decimal]:
    """
    گرفتن قیمت فعلی از Binance
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_API}/ticker/price",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                return Decimal(data["price"])
            
            return None
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None


async def get_multiple_prices(symbols: list[str]) -> dict[str, Decimal]:
    """
    گرفتن قیمت چند ارز
    """
    prices = {}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BINANCE_API}/ticker/price")
            
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    if item["symbol"] in symbols:
                        prices[item["symbol"]] = Decimal(item["price"])
    except Exception as e:
        print(f"Error fetching prices: {e}")
    
    return prices
