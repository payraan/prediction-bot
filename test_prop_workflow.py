import asyncio
import sys
from decimal import Decimal

sys.path.insert(0, '.')

async def test_prop_engine():
    from src.database.connection import async_session
    from sqlalchemy import select
    from src.database.models import User, Balance, Market, MarketType, PredictionDirection
    from src.core.services.prop_service import buy_prop_challenge, place_prop_prediction

    async with async_session() as session:
        print("🔍 در حال جستجوی یک کاربر در دیتابیس...")
        user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        
        if not user:
            print("❌ هیچ کاربری در دیتابیس پیدا نشد. لطفاً ربات تلگرام را یکبار استارت کن.")
            return

        print(f"👤 کاربر پیدا شد: {user.telegram_id}")

        # ۱. شارژ حساب واقعی با ۱۰۰ تتر برای تست
        stmt = select(Balance).where(Balance.user_id == user.id, Balance.asset == "USDT")
        balance = (await session.execute(stmt)).scalar_one_or_none()
        
        if not balance:
            balance = Balance(user_id=user.id, currency="USDT", asset="USDT", network="TRC20", available=Decimal("100"))
            session.add(balance)
        else:
            balance.available = Decimal("100")
            
        await session.commit()
        print("💰 حساب واقعی کاربر با ۱۰۰ USDT شارژ شد.")

        # ۲. خرید چالش ۱۰ هزار دلاری
        print("🛒 در حال خرید چالش ۱۰,۰۰۰ دلاری...")
        try:
            prop_account = await buy_prop_challenge(session, user.id, Decimal("10000"))
            print(f"✅ چالش با موفقیت خریداری شد! موجودی مجازی: {prop_account.virtual_balance} دلار")
        except Exception as e:
            print(f"❌ خطا در خرید چالش: {e}")
            return

        # ۳. پیدا کردن یک مارکت معتبر پالی‌مارکت (شرط قیمت بین ۰.۱۵ تا ۰.۸۵)
        stmt_market = select(Market).where(
            Market.market_type == MarketType.POLYMARKET,
            Market.yes_price >= Decimal("0.15"),
            Market.yes_price <= Decimal("0.85")
        ).limit(1)
        market = (await session.execute(stmt_market)).scalar_one_or_none()

        if not market:
            print("⚠️ مارکت مناسبی در دیتابیس پیدا نشد.")
            return

        print(f"📊 مارکت انتخاب شد: {market.title[:50]}... | قیمت YES: {market.yes_price}")

        # ۴. ثبت پیش‌بینی پراپ
        print("🎯 در حال ثبت پیش‌بینی ५۰۰ دلاری...")
        try:
            prediction = await place_prop_prediction(
                session=session,
                prop_account_id=prop_account.id,
                market_id=market.id,
                direction=PredictionDirection.YES,
                amount=Decimal("500")
            )
            print(f"✅ پیش‌بینی با موفقیت ثبت شد! شناسه: {prediction.id}")
            
            # گرفتن موجودی جدید
            await session.refresh(prop_account)
            print(f"💵 موجودی مجازی باقیمانده: {prop_account.virtual_balance} دلار")
        except Exception as e:
            print(f"❌ خطا در ثبت پیش‌بینی: {e}")

if __name__ == "__main__":
    asyncio.run(test_prop_engine())
