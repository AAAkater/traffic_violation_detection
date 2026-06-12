"""模型提供商管理业务逻辑。"""

from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.tables import ModelProvider
from detector.models.provider import ModelInfo, ProviderCreate, ProviderData, ProviderModelsData, ProviderUpdate
from detector.repositories.provider import ModelProviderRepo
from detector.utils import logger


def _mask_api_key(key: str) -> str:
    """对 API 密钥进行脱敏处理，只保留前 4 位和后 4 位。"""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


def _to_provider_data(p: ModelProvider) -> ProviderData:
    """将 ORM 对象转换为响应模型。"""
    return ProviderData(
        id=p.id,
        name=p.name,
        base_url=p.base_url,
        api_key=_mask_api_key(p.api_key),
        activated_models=p.activated_models or [],
        created_at=str(p.created_at),
        updated_at=str(p.updated_at),
    )


class ProviderService:
    """模型提供商管理业务逻辑服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ModelProviderRepo(session)

    async def create_provider(self, body: ProviderCreate) -> ProviderData:
        """创建模型提供商配置。

        Args:
            body: 创建请求体。

        Returns:
            ProviderData 创建后的提供商数据。

        Raises:
            ValueError: 提供商名称已存在。
        """
        existing = await self._repo.get_by_name(body.name)
        if existing is not None:
            raise ValueError(f"提供商名称已存在: {body.name}")

        provider = ModelProvider(
            name=body.name,
            base_url=body.base_url,
            api_key=body.api_key,
        )
        await self._repo.create(provider)

        await self._session.flush()
        await self._session.refresh(provider)

        logger.info(f"[provider] 创建提供商: name={body.name}")
        return _to_provider_data(provider)

    async def get_provider(self, provider_id: int) -> ProviderData | None:
        """获取指定 ID 的模型提供商配置。"""
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            return None
        return _to_provider_data(provider)

    async def list_providers(self) -> list[ProviderData]:
        """列出所有模型提供商配置。"""
        providers = await self._repo.list_all()
        return [_to_provider_data(p) for p in providers]

    async def update_provider(self, provider_id: int, body: ProviderUpdate) -> ProviderData:
        """更新模型提供商配置。

        只更新请求体中提供的字段，未提供的字段保持不变。

        Args:
            provider_id: 提供商 ID。
            body: 更新请求体。

        Returns:
            ProviderData 更新后的提供商数据。

        Raises:
            ValueError: 提供商不存在或名称冲突。
        """
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"未找到提供商: {provider_id}")

        # 检查名称唯一性
        if body.name is not None and body.name != provider.name:
            existing = await self._repo.get_by_name(body.name)
            if existing is not None:
                raise ValueError(f"提供商名称已存在: {body.name}")

        # 只更新提供的字段
        if body.name is not None:
            provider.name = body.name
        if body.base_url is not None:
            provider.base_url = body.base_url
        if body.api_key is not None:
            provider.api_key = body.api_key
        provider.updated_at = datetime.now()

        logger.info(f"[provider] 更新提供商: id={provider_id}")
        return _to_provider_data(provider)

    async def delete_provider(self, provider_id: int) -> dict:
        """删除模型提供商配置。

        Args:
            provider_id: 提供商 ID。

        Returns:
            包含 id 的信息。

        Raises:
            ValueError: 提供商不存在。
        """
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"未找到提供商: {provider_id}")

        await self._repo.delete(provider)
        logger.info(f"[provider] 删除提供商: id={provider_id}, name={provider.name}")

        return {"id": provider_id, "msg": "模型提供商已删除"}

    async def list_models(self, provider_id: int) -> ProviderModelsData:
        """通过 OpenAI SDK 列出指定提供商的所有可用模型。

        Args:
            provider_id: 提供商 ID。

        Returns:
            ProviderModelsData 包含提供商信息和模型列表。

        Raises:
            ValueError: 提供商不存在。
        """
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"未找到提供商: {provider_id}")

        client = AsyncOpenAI(base_url=provider.base_url, api_key=provider.api_key)
        try:
            models_page = await client.models.list()
            models = [
                ModelInfo(
                    id=m.id,
                    owned_by=m.owned_by or "",
                    created=m.created,
                )
                for m in models_page.data
            ]
            logger.info(f"[provider] 列出提供商 {provider.name} 的模型: {len(models)} 个")
        except Exception as e:
            logger.error(f"[provider] 列出模型失败: {e}")
            raise RuntimeError(f"获取模型列表失败: {e}") from e

        return ProviderModelsData(
            provider_id=provider.id,
            provider_name=provider.name,
            models=models,
        )

    async def activate_model(self, provider_id: int, model: str) -> ProviderData:
        """激活指定提供商的某个模型。

        Args:
            provider_id: 提供商 ID。
            model: 要激活的模型名称。

        Returns:
            ProviderData 更新后的提供商数据。

        Raises:
            ValueError: 提供商不存在。
        """
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"未找到提供商: {provider_id}")

        activated = list(provider.activated_models or [])
        if model not in activated:
            activated.append(model)
            provider.activated_models = activated
            provider.updated_at = datetime.now()
            logger.info(f"[provider] 激活模型: provider={provider.name}, model={model}")
        else:
            logger.debug(f"[provider] 模型已激活，跳过: provider={provider.name}, model={model}")

        return _to_provider_data(provider)

    async def deactivate_model(self, provider_id: int, model: str) -> ProviderData:
        """停用指定提供商的某个模型。

        Args:
            provider_id: 提供商 ID。
            model: 要停用的模型名称。

        Returns:
            ProviderData 更新后的提供商数据。

        Raises:
            ValueError: 提供商不存在或模型未激活。
        """
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"未找到提供商: {provider_id}")

        activated = list(provider.activated_models or [])
        if model not in activated:
            raise ValueError(f"模型 {model} 未激活，无法停用")

        activated.remove(model)
        provider.activated_models = activated if activated else None
        provider.updated_at = datetime.now()
        logger.info(f"[provider] 停用模型: provider={provider.name}, model={model}")

        return _to_provider_data(provider)

    async def list_activated_models(self, provider_id: int) -> list[str]:
        """获取指定提供商的所有已激活模型。

        Args:
            provider_id: 提供商 ID。

        Returns:
            已激活的模型名称列表。

        Raises:
            ValueError: 提供商不存在。
        """
        provider = await self._repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"未找到提供商: {provider_id}")

        return list(provider.activated_models or [])

    async def get_provider_config(self, provider_id: int) -> ModelProvider | None:
        """获取指定 ID 的模型提供商配置（供 judge 服务调用）。

        Returns:
            ModelProvider 对象，如果没有则返回 None。
        """
        return await self._repo.get_by_id(provider_id)
