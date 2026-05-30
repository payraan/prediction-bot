from datetime import datetime, timedelta
from sqlalchemy import select
from src.database.connection import async_session
from src.database.models import User
from src.core.services.local_market_service import create_local_market

async def process_newmarket_command(telegram_id: int, command_text: str) -> str:
    """
    پردازش کامند تلگرامی ساخت بازار بومی
    فرمت ورودی: عنوان | توضیحات | دسته‌بندی | تعداد ساعت
    """
    try:
        # جدا کردن بخش‌های مختلف کامند با کاراکتر |
        parts = [p.strip() for p in command_text.split('|')]
        if len(parts) != 4:
            return (
                "❌ **فرمت دستور اشتباه است!**\n\n"
                "لطفاً دقیقاً به این شکل ارسال کنید:\n"
                "`/newmarket عنوان | توضیحات | دسته بندی | ساعت`\n\n"
                "مثال:\n"
                "`/newmarket دربی تهران | پرسپولیس میبره؟ | SPORTS | 24`"
            )
        
        title, description, category, hours_str = parts
        hours = int(hours_str)

        async with async_session() as session:
            # ۱. بررسی اینکه آیا کاربر ادمین (System User) است؟
            stmt = select(User).where(User.telegram_id == telegram_id)
            admin = (await session.execute(stmt)).scalar_one_or_none()

            if not admin or not admin.is_system_user:
                return "⛔️ عدم دسترسی! شما ادمین تایید شده سیستم نیستید."

            # ۲. محاسبه زمان بسته شدن (پریود زمانی)
            closes_at = datetime.utcnow() + timedelta(hours=hours)

            # ۳. ثبت بازار بومی در دیتابیس
            market = await create_local_market(
                session=session,
                title=title,
                description=description,
                category=category,
                closes_at=closes_at,
                admin_id=admin.id
            )
            
            return (
                "✅ **بازار بومی با موفقیت در دیتابیس ثبت شد!**\n\n"
                f"📌 **عنوان:** {market.title}\n"
                f"🗂 **دسته‌بندی:** {market.category}\n"
                f"⏳ **بسته شدن در:** {hours} ساعت دیگر\n"
                f"🆔 **شناسه:** `{market.id}`\n\n"
                "کاربران اکنون می‌توانند روی این بازار پیش‌بینی ثبت کنند."
            )
            
    except ValueError:
        return "❌ **خطا:** مقدار «ساعت» باید یک عدد صحیح باشد (مثلاً 24)."
    except Exception as e:
        return f"❌ **خطای سیستمی در ثبت بازار:** {e}"
