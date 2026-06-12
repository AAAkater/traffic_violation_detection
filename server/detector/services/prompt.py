"""系统提示词管理业务逻辑。"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from detector.models.prompt import PromptData, PromptListItem
from detector.repositories.prompt import SystemPromptRepo
from detector.settings import settings
from detector.utils import logger


class PromptService:
    """系统提示词管理业务逻辑服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SystemPromptRepo(session)

    async def set_prompt(self, name: str, content: str) -> PromptData:
        """创建或更新系统提示词，并设为激活。

        Args:
            name: 提示词名称。
            content: 提示词内容。

        Returns:
            PromptData 更新后的提示词数据。
        """
        # 将所有现有提示词设为非激活
        await self._repo.deactivate_all()

        # 查找是否已存在同名提示词
        from detector.db.tables import SystemPrompt

        existing = await self._repo.get_by_name(name)
        if existing:
            existing.content = content
            existing.is_active = True
            existing.updated_at = datetime.now()
            logger.info(f"[prompt] 更新提示词: name={name}")
        else:
            prompt = SystemPrompt(name=name, content=content, is_active=True)
            await self._repo.create(prompt)
            logger.info(f"[prompt] 创建提示词: name={name}")

        return PromptData(name=name, content=content)

    async def get_active_prompt(self) -> PromptData:
        """获取当前激活的系统提示词。"""
        active = await self._repo.get_active()
        if active:
            return PromptData(name=active.name, content=active.content)
        return PromptData(name="default", content=settings.default_system_prompt)

    async def list_prompts(self) -> list[PromptListItem]:
        """列出所有系统提示词。"""
        prompts = await self._repo.list_all()
        return [
            PromptListItem(
                name=p.name,
                content=p.content,
                is_active=p.is_active,
                updated_at=str(p.updated_at),
            )
            for p in prompts
        ]

    async def get_system_prompt_text(self) -> str:
        """获取当前生效的系统提示词文本（供 judge 服务调用）。"""
        active = await self._repo.get_active()
        if active and active.content:
            return active.content
        return settings.default_system_prompt
