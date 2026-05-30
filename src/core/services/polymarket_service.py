import uuid
import json
import httpx
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dateutil.parser import parse

from src.database.models import Market, MarketType, MarketStatus

POLYMARKET_API_URL = "https://gamma-api.polymarket.com/events"

async def sync_polymarket_events(session: AsyncSession):
    """دریافت دیتای زنده از Polymarket و به‌روزرسانی دیتابیس"""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # گرفتن رویدادهای فعال
        response = await client.get(
            POLYMARKET_API_URL, 
            params={"active": "true", "closed": "false", "limit": 50}
        )
        response.raise_for_status()
        events = response.json()
    print(f"📦 دریافت {len(events)} رویداد خام از Polymarket API")

    added_count = 0
    updated_count = 0

    for event in events:
        markets = event.get("markets", [])
        for m in markets:
            if not m.get("active") or m.get("closed"):
                continue
            
            # فرض می‌کنیم مارکت‌های با دو خروجی مد نظر است (YES/NO)
            outcomes = m.get("outcomes", [])
            if len(outcomes) != 2 or outcomes[0].upper() != "YES" or outcomes[1].upper() != "NO":
                continue

            condition_id = m.get("conditionId")
            if not condition_id:
                continue

            # استخراج قیمت‌ها
            prices = m.get("outcomePrices")
            if not prices or len(prices) < 2:
                continue
            try:
                yes_price = Decimal(str(prices[0]))
                no_price = Decimal(str(prices[1]))
            except (ValueError, IndexError):
                continue
            
            # پارس کردن زمان پایان
            end_date_str = m.get("endDate")
            closes_at = parse(end_date_str).replace(tzinfo=None) if end_date_str else datetime.utcnow()

            # بررسی وجود مارکت در دیتابیس
            stmt = select(Market).where(Market.polymarket_condition_id == condition_id)
            result = await session.execute(stmt)
            existing_market = result.scalar_one_or_none()

            if existing_market:
                # آپدیت قیمت‌های لحظه‌ای
                existing_market.yes_price = yes_price
                existing_market.no_price = no_price
                existing_market.status = MarketStatus.ACTIVE
                updated_count += 1
            else:
                # ساخت مارکت جدید برای شبیه‌ساز پراپ
                new_market = Market(
                    title=m.get("question", event.get("title")),
                    description=event.get("description", ""),
                    category=m.get("groupItemTitle", "General"),
                    market_type=MarketType.POLYMARKET,
                    status=MarketStatus.ACTIVE,
                    polymarket_condition_id=condition_id,
                    yes_price=yes_price,
                    no_price=no_price,
                    closes_at=closes_at,
                    eligible_for_prop=True
                )
                session.add(new_market)
                added_count += 1

    await session.commit()
    return {"added": added_count, "updated": updated_count}
