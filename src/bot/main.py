"""
Telegram Bot Main
ربات اصلی تلگرام
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from src.core.config import get_settings
from src.database.connection import async_session
from src.core.services.user_service import get_or_create_user, get_user_balance

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# گرفتن تنظیمات
settings = get_settings()

# ساخت Bot و Dispatcher
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """دستور /start"""
    
    user = message.from_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    # ثبت کاربر در دیتابیس
    async with async_session() as session:
        db_user = await get_or_create_user(
            session=session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        logger.info(f"User saved/updated in DB: {db_user.id}")
    
    # دکمه‌های منو با WebApp
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 شروع بازی",
            web_app=WebAppInfo(url=settings.webapp_url)
        )],
        [InlineKeyboardButton(text="💰 موجودی", callback_data="balance")],
        [InlineKeyboardButton(text="📥 واریز", callback_data="deposit")],
        [InlineKeyboardButton(text="📤 برداشت", callback_data="withdraw")],
    ])
    
    await message.answer(
        f"👋 سلام {user.first_name}!\n\n"
        "🎯 به بازی پیش‌بینی قیمت TON خوش آمدید!\n\n"
        "📈 قیمت بیتکوین بالا می‌ره یا پایین؟\n"
        "پیش‌بینی کن و برنده شو! 🏆",
        reply_markup=keyboard
    )


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """دستور /balance"""
    
    async with async_session() as session:
        balance = await get_user_balance(session, message.from_user.id)
        
        if balance:
            await message.answer(
                "💰 موجودی شما:\n\n"
                f"├ موجودی قابل برداشت: {balance.available:.2f} TON\n"
                f"├ در حال بازی: {balance.locked:.2f} TON\n"
                f"└ مجموع: {(balance.available + balance.locked):.2f} TON"
            )
        else:
            await message.answer("❌ لطفاً اول /start بزنید.")


@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    """هندل کردن دکمه‌های inline"""
    
    if callback.data == "balance":
        async with async_session() as session:
            balance = await get_user_balance(session, callback.from_user.id)
            
            if balance:
                await callback.message.answer(
                    "💰 موجودی شما:\n\n"
                    f"├ موجودی قابل برداشت: {balance.available:.2f} TON\n"
                    f"├ در حال بازی: {balance.locked:.2f} TON\n"
                    f"└ مجموع: {(balance.available + balance.locked):.2f} TON"
                )
            else:
                await callback.message.answer("❌ لطفاً اول /start بزنید.")
    
    elif callback.data == "deposit":
        await callback.message.answer(
            "📥 برای واریز، TON رو به آدرس زیر بفرست:\n\n"
            f"`{settings.ton_house_wallet_address}`\n\n"
            "⚠️ حتماً با memo مخصوص خودت بفرست!",
            parse_mode="Markdown"
        )
    
    elif callback.data == "withdraw":
        await callback.message.answer(
            "📤 برداشت:\n\n"
            "برای برداشت از دستور زیر استفاده کن:\n"
            "`/withdraw [مقدار] [آدرس]`",
            parse_mode="Markdown"
        )
    
    await callback.answer()


async def main():
    """شروع ربات"""
    logger.info("🚀 Bot is starting...")
    logger.info(f"📱 WebApp URL: {settings.webapp_url}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
