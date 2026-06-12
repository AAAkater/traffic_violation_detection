"""系统提示词的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.tables import SystemPrompt


class SystemPromptRepo:
    """系统提示词数据仓库。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self) -> SystemPrompt | None:
        """获取当前激活的系统提示词。"""
        result = await self._session.execute(
            select(SystemPrompt).where(SystemPrompt.is_active.is_(True)).order_by(SystemPrompt.updated_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> SystemPrompt | None:
        """根据名称查询系统提示词。"""
        result = await self._session.execute(select(SystemPrompt).where(SystemPrompt.name == name))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[SystemPrompt]:
        """列出所有系统提示词。"""
        result = await self._session.execute(select(SystemPrompt).order_by(SystemPrompt.created_at.desc()))
        return list(result.scalars().all())

    async def deactivate_all(self) -> None:
        """将所有提示词设为非激活。"""
        result = await self._session.execute(select(SystemPrompt).where(SystemPrompt.is_active.is_(True)))
        for old in result.scalars().all():
            old.is_active = False

    async def create(self, prompt: SystemPrompt) -> SystemPrompt:
        """创建系统提示词。"""
        self._session.add(prompt)
        return prompt
