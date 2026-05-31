import logging
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

_CATEGORY_MAP = [
    ("crypto", "Crypto"), ("bitcoin", "Crypto"), ("ethereum", "Crypto"), ("defi", "Crypto"),
    ("politic", "Politics"), ("election", "Politics"), ("president", "Politics"), ("government", "Politics"),
    ("sport", "Sports"), ("nba", "Sports"), ("nfl", "Sports"), ("soccer", "Sports"), ("football", "Sports"),
    ("tech", "Tech"), ("ai ", "Tech"), ("openai", "Tech"), ("spacex", "Tech"),
    ("business", "Business"), ("econom", "Business"), ("stock", "Business"),
    ("finance", "Finance"), ("fed", "Finance"), ("rate", "Finance"), ("inflation", "Finance"),
    ("geopolit", "Geopolitics"), ("war", "Geopolitics"), ("nato", "Geopolitics"), ("russia", "Geopolitics"),
    ("science", "Science"), ("pop culture", "Pop Culture"), ("entertainment", "Pop Culture"), ("movie", "Pop Culture"),
    ("weather", "Weather"), ("hurricane", "Weather")
]

_TITLE_KEYWORDS = [
    ("bitcoin", "Crypto"), ("btc", "Crypto"), ("eth", "Crypto"), ("solana", "Crypto"),
    ("trump", "Politics"), ("biden", "Politics"), ("harris", "Politics"), ("election", "Politics"),
    ("nba", "Sports"), ("nfl", "Sports"), ("cup", "Sports"), ("champion", "Sports"),
    ("openai", "Tech"), ("gpt", "Tech"), ("spacex", "Tech"),
    ("fed ", "Finance"), ("rate cut", "Finance"),
    ("invades", "Geopolitics"), ("war ", "Geopolitics"), ("iran", "Geopolitics")
]

def _canonicalize_category(raw_category: str, title: str) -> str:
    raw = (raw_category or "").lower().strip()
    title_l = (title or "").lower()
    for substring, canonical in _CATEGORY_MAP:
        if substring in raw:
            return canonical
    for keyword, canonical in _TITLE_KEYWORDS:
        if keyword in title_l:
            return canonical
    return "Other"

async def sync_polymarket_events(session: AsyncSession):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.get(POLYMARKET_API_URL, params={"active": "true", "closed": "false", "limit": 100})
        response.raise_for_status()
        events = response.json()
    
    added_count = 0
    updated_count = 0
    
    for event in events:
        markets = event.get("markets", [])
        for m in markets:
            condition_id = m.get("conditionId")
            if not condition_id or str(m.get("active")).lower() != "true":
                continue
                
            prices = m.get("outcomePrices", [])
            if isinstance(prices, str):
                try: prices = json.loads(prices)
                except: continue
            if not isinstance(prices, list) or len(prices) < 2:
                continue
                
            try:
                yes_price = Decimal(str(prices[0]))
                no_price  = Decimal(str(prices[1]))
            except:
                continue
                
            title = m.get("question") or event.get("title") or ""
            raw_cat = m.get("groupItemTitle") or event.get("category") or ""
            canonical_category = _canonicalize_category(raw_cat, title)
            
            end_date_str = m.get("endDate")
            closes_at = parse(end_date_str).replace(tzinfo=None) if end_date_str else datetime.utcnow()
            
            stmt = select(Market).where(Market.polymarket_condition_id == condition_id)
            result = await session.execute(stmt)
            existing_market = result.scalar_one_or_none()
            
            if existing_market:
                existing_market.yes_price = yes_price
                existing_market.no_price = no_price
                existing_market.category = canonical_category
                updated_count += 1
            else:
                new_market = Market(
                    title=title,
                    description=event.get("description", ""),
                    category=canonical_category,
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
    return {"added": added_count, "updated": updated_count}\n