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
from src.core.services.user_service import get_or_create_user, get_user_balances
from src.core.services.deposit_address_service import get_or_create_deposit_address

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# گرفتن تنظیمات
settings = get_settings()

# Admin Helper
def is_admin(message: types.Message) -> bool:
    """Check if user is admin"""
    return (settings.admin_telegram_chat_id is not None and 
            message.from_user.id == settings.admin_telegram_chat_id)

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
        balances = await get_user_balances(session, message.from_user.id)
        
        if balances:
            lines = ["💰 موجودی شما:\n"]
            for b in balances:
                asset = getattr(b, "asset", getattr(b, "currency", ""))
                network = getattr(b, "network", "")
                avail = float(getattr(b, "available", 0) or 0)
                locked = float(getattr(b, "locked", 0) or 0)
                lines.append(f"• {asset}/{network}  |  قابل برداشت: {avail:.2f}  |  در حال بازی: {locked:.2f}")
            await message.answer("\n".join(lines))
        else:
            await message.answer("❌ لطفاً اول /start بزنید.")


@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    """هندل کردن دکمه‌های inline"""
    
    if callback.data == "balance":
        async with async_session() as session:
            balances = await get_user_balances(session, callback.from_user.id)
            
            if balances:
                lines = ["💰 موجودی شما:\n"]
                for b in balances:
                    asset = getattr(b, "asset", getattr(b, "currency", ""))
                    network = getattr(b, "network", "")
                    avail = float(getattr(b, "available", 0) or 0)
                    locked = float(getattr(b, "locked", 0) or 0)
                    lines.append(f"• {asset}/{network}  |  قابل برداشت: {avail:.2f}  |  در حال بازی: {locked:.2f}")
                await callback.message.answer("\n".join(lines))
            else:
                await callback.message.answer("❌ لطفاً اول /start بزنید.")
    
    elif callback.data == "deposit":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="TON (Legacy)", callback_data="deposit:TON:TON")],
            [InlineKeyboardButton(text="USDT - TRC20", callback_data="deposit:USDT:TRC20")],
        ])
        await callback.message.answer(
            "📥 روش واریز رو انتخاب کن:",
            reply_markup=keyboard
        )
    
    elif callback.data == "deposit:TON:TON":
        await callback.message.answer(
            "📥 واریز TON (Legacy):\n\n"
            f"`{settings.ton_house_wallet_address}`\n\n"
            "ℹ️ memo فعلاً در نسخه Legacy از سمت Bot نمایش داده نمی‌شود.",
            parse_mode="Markdown"
        )

    elif callback.data == "deposit:USDT:TRC20":
        async with async_session() as session:
            da = await get_or_create_deposit_address(
                session=session,
                telegram_id=callback.from_user.id,
                asset="USDT",
                network="TRC20",
            )
        await callback.message.answer(
            "📥 واریز USDT روی شبکه TRC20:\n\n"
            f"آدرس اختصاصی شما:\n`{da.address}`\n\n"
            "⚠️ فقط USDT (TRC20) به این آدرس بفرست.\n"
            "❌ ارسال روی شبکه‌های دیگر باعث از دست رفتن دارایی می‌شود.",
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

@dp.message(Command("admin_withdrawals"))
async def cmd_admin_withdrawals(message: types.Message):
    """List withdrawals needing review (Admin only)"""
    if not is_admin(message):
        return
    
    from src.core.services.withdrawal_service import get_needs_review_withdrawals
    async with async_session() as session:
        items = await get_needs_review_withdrawals(session)
    
    if not items:
        return await message.answer("✅ هیچ برداشت نیازمند بررسی نداریم.")
    
    text = "🧾 برداشت‌های NEEDS_REVIEW:\n\n"
    for w in items[:10]:
        text += f"ID: `{w.id}`\n"
        text += f"├ مبلغ: {w.amount} TON\n"
        text += f"├ آدرس: `{w.to_address[:20]}...`\n"
        text += f"└ تاریخ: {w.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("admin_approve"))
async def cmd_admin_approve(message: types.Message):
    """Approve withdrawal (Admin only)"""
    if not is_admin(message):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("فرمت: /admin_approve <withdrawal_uuid>")
    
    import uuid
    try:
        wid = uuid.UUID(parts[1])
    except ValueError:
        return await message.answer("❌ UUID نامعتبر است")
    
    from src.core.services.withdrawal_service import approve_withdrawal
    async with async_session() as session:
        try:
            w = await approve_withdrawal(session, wid, admin_note="approved via bot")
            await message.answer(f"✅ Approved: {w.id}\nStatus: {w.status}")
        except Exception as e:
            await message.answer(f"❌ خطا: {e}")


@dp.message(Command("admin_cancel"))
async def cmd_admin_cancel(message: types.Message):
    """Cancel withdrawal (Admin only)"""
    if not is_admin(message):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("فرمت: /admin_cancel <withdrawal_uuid> [reason]")
    
    import uuid
    try:
        wid = uuid.UUID(parts[1])
    except ValueError:
        return await message.answer("❌ UUID نامعتبر است")
    
    reason = " ".join(parts[2:]) if len(parts) > 2 else "cancelled via bot"
    
    from src.core.services.withdrawal_service import cancel_withdrawal
    async with async_session() as session:
        try:
            w = await cancel_withdrawal(session, wid, reason=reason)
            await message.answer(f"🟠 Cancelled: {w.id}\nStatus: {w.status}")
        except Exception as e:
            await message.answer(f"❌ خطا: {e}")

@dp.message(Command("admin_fund_ghost"))
async def cmd_admin_fund_ghost(message: types.Message):
    """Fund Ghost Bot (Admin only)"""
    if not is_admin(message):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("فرمت: /admin_fund_ghost <amount_in_TON>")
    
    try:
        amount = float(parts[1])
        if amount <= 0:
            return await message.answer("❌ مقدار باید مثبت باشه")
    except ValueError:
        return await message.answer("❌ مقدار نامعتبر است")
    
    from decimal import Decimal
    from sqlalchemy import select, update
    from src.database.models import User, Balance, Ledger, LedgerEventType
    from src.core.config import get_settings
    
    settings = get_settings()
    
    async with async_session() as session:
        # Get or create ghost user
        from src.core.services.user_service import get_or_create_user
        ghost = await get_or_create_user(
            session=session,
            telegram_id=settings.ghost_bot_telegram_id,
            username="ghost_liquidity_bot",
            first_name="GhostBot"
        )
        
        # Get balance
        res = await session.execute(select(Balance).where(Balance.user_id == ghost.id))
        bal = res.scalar_one_or_none()
        
        if not bal:
            bal = Balance(
                user_id=ghost.id,
                available=Decimal("0"),
                locked=Decimal("0"),
                currency="TON"
            )
            session.add(bal)
            await session.flush()
        
        # Add funds
        bal.available += Decimal(str(amount))
        
        # Create ledger entry
        ledger = Ledger(
            user_id=ghost.id,
            amount=Decimal(str(amount)),
            balance_after=bal.available,
            event_type=LedgerEventType.DEPOSIT_CREDITED,
            description=f"Admin funded Ghost Bot: {amount} TON"
        )
        session.add(ledger)
        
        await session.commit()
        
        await message.answer(
            f"✅ Ghost Bot Funded!\n\n"
            f"├ مبلغ: {amount} TON\n"
            f"├ موجودی جدید: {bal.available} TON\n"
            f"└ Bot ID: {ghost.telegram_id}"
        )

async def main():
    """شروع ربات"""
    logger.info("🚀 Bot is starting...")
    logger.info(f"📱 WebApp URL: {settings.webapp_url}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
