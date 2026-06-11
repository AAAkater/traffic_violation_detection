"""数据库引擎与会话管理。"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from detector.settings import settings

# ── 异步引擎 ──
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# ── 异步会话工厂 ──
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 基类。"""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取异步数据库会话。"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
