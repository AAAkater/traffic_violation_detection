"""模型提供商的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.tables import ModelProvider


class ModelProviderRepo:
    """模型提供商数据仓库。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, provider_id: int) -> ModelProvider | None:
        """根据 ID 查询提供商。"""
        result = await self._session.execute(select(ModelProvider).where(ModelProvider.id == provider_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> ModelProvider | None:
        """根据名称查询提供商。"""
        result = await self._session.execute(select(ModelProvider).where(ModelProvider.name == name))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ModelProvider]:
        """列出所有提供商。"""
        result = await self._session.execute(select(ModelProvider).order_by(ModelProvider.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, provider: ModelProvider) -> ModelProvider:
        """创建提供商。"""
        self._session.add(provider)
        return provider

    async def delete(self, provider: ModelProvider) -> None:
        """删除提供商。"""
        await self._session.delete(provider)
