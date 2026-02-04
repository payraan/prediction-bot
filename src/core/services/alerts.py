# src/core/services/alerts.py
from typing import Optional
from aiogram import Bot
from src.core.config import get_settings

settings = get_settings()

_bot: Optional[Bot] = None


def _get_bot() -> Optional[Bot]:
    """Get or create bot instance for alerts"""
    global _bot
    if not settings.telegram_bot_token or not settings.admin_telegram_chat_id:
        return None
    if _bot is None:
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


async def alert_admin(text: str):
    """Send alert message to admin"""
    bot = _get_bot()
    if not bot:
        # Silent fail - no admin configured
        return
    try:
        await bot.send_message(chat_id=settings.admin_telegram_chat_id, text=text)
    except Exception as e:
        # Last line of defense - don't crash the system
        print(f"[ALERT FAILED] {text} | Error: {e}")
