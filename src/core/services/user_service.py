"""
User Service
سرویس مدیریت کاربران
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import get_settings
from src.database.models import User, Balance
from decimal import Decimal
import uuid

settings = get_settings()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str = None,
    first_name: str = None
) -> User:
    """گرفتن یا ساختن کاربر جدید"""
    
    # چک کن کاربر وجود داره
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # آپدیت اطلاعات
        user.username = username
        user.first_name = first_name
    else:
        # کاربر جدید بساز
        user = User(
            id=uuid.uuid4(),
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        session.add(user)
        await session.flush()
        
        # موجودی اولیه بساز
        balance = Balance(
            id=uuid.uuid4(),
            user_id=user.id,
            available=Decimal("0"),
            locked=Decimal("0"),
            currency=settings.default_asset,
            asset=settings.default_asset,
            network=settings.default_network,
        )
        session.add(balance)
    
    # فقط یک commit در انتها
    await session.commit()
    return user


async def get_user_balance(session: AsyncSession, telegram_id: int) -> Balance:
    """گرفتن موجودی کاربر"""
    
    result = await session.execute(
        select(Balance)
        .join(User)
        .where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def get_user_balances(session: AsyncSession, telegram_id: int) -> list[Balance]:
    """گرفتن همه موجودی‌های کاربر (Multi-Asset/Multi-Network)"""
    result = await session.execute(
        select(Balance)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Balance.asset.asc(), Balance.network.asc())
    )
    return list(result.scalars().all())
