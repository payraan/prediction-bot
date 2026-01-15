"""
Database Connection
مدیریت اتصال به دیتابیس
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.core.config import get_settings
from src.database.models import Base

settings = get_settings()

# تبدیل URL به فرمت async
DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# ساخت Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,  # لاگ SQL فقط در حالت DEBUG
    pool_size=10,
    max_overflow=20
)

# Session Factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """ساخت جداول در دیتابیس"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ جداول دیتابیس ساخته شدن!")


async def get_session() -> AsyncSession:
    """گرفتن یک Session جدید"""
    async with async_session() as session:
        yield session
