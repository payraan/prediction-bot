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


async def get_user_balance(
    session: AsyncSession,
    telegram_id: int,
    asset: str | None = None,
    network: str | None = None,
) -> Balance | None:
    """
    گرفتن موجودی کاربر برای یک (asset, network) مشخص.
    برای سازگاری با multi-asset اگر ورودی ندی از defaults استفاده می‌کنیم.
    اگر چند ردیف هم وجود داشته باشد، اولین مورد برگردانده می‌شود (بدون crash).
    """
    a = (asset or settings.default_asset or "TON").strip().upper()
    n = (network or settings.default_network or "").strip().upper()

    q = (
        select(Balance)
        .join(User)
        .where(
            User.telegram_id == telegram_id,
            Balance.asset == a,
            Balance.network == n,
        )
        .order_by(Balance.id.desc())
    )

    result = await session.execute(q)
    return result.scalars().first()

async def get_user_balances(session: AsyncSession, telegram_id: int) -> list[Balance]:
    """گرفتن همه موجودی‌های کاربر (Multi-Asset/Multi-Network)"""
    result = await session.execute(
        select(Balance)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Balance.asset.asc(), Balance.network.asc())
    )
    return list(result.scalars().all())
