"""数据库引擎与会话管理。"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from detector.settings import settings

# ── 异步引擎 ──
db_engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# ── 异步会话工厂 ──
async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 基类。"""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取异步数据库会话。

    使用 yield 模式确保会话在请求结束后自动关闭，
    发生异常时自动回滚。
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Annotated 类型别名，供路由端点使用 ──
SessionDep = Annotated[AsyncSession, Depends(get_db)]
