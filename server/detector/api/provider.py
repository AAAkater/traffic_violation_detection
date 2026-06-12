"""模型提供商端点 — 管理 LLM 判定模型的连接配置。

用户通过此接口增删改查模型提供商配置，替代环境变量方式。
同一时间只能有一个激活的提供商。
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.common.response import ProviderCreate, ProviderData, ProviderUpdate, Response
from detector.db import ModelProvider, SessionDep
from detector.utils import logger

router = APIRouter(tags=["provider"])


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
        model=p.model,
        base_url=p.base_url,
        api_key=_mask_api_key(p.api_key),
        is_active=p.is_active,
        created_at=str(p.created_at),
        updated_at=str(p.updated_at),
    )


@router.post("/provider")
async def create_provider(
    body: ProviderCreate,
    db: SessionDep,
) -> Response[ProviderData]:
    """创建模型提供商配置。

    创建后自动设为激活状态（其他提供商将被停用）。
    """
    # 检查名称是否已存在
    result = await db.execute(select(ModelProvider).where(ModelProvider.name == body.name))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"提供商名称已存在: {body.name}")

    # 将所有现有提供商设为非激活
    result = await db.execute(select(ModelProvider).where(ModelProvider.is_active.is_(True)))
    for old in result.scalars().all():
        old.is_active = False

    provider = ModelProvider(
        name=body.name,
        model=body.model,
        base_url=body.base_url,
        api_key=body.api_key,
        is_active=True,
    )
    db.add(provider)
    logger.info(f"[provider] 创建提供商: name={body.name}, model={body.model}")

    # 需要刷新以获取自增 ID 和默认值
    await db.flush()
    await db.refresh(provider)

    return Response(msg="模型提供商已创建", data=_to_provider_data(provider))


@router.get("/provider")
async def get_active_provider(db: SessionDep) -> Response[ProviderData | None]:
    """获取当前激活的模型提供商配置。"""
    result = await db.execute(
        select(ModelProvider).where(ModelProvider.is_active.is_(True)).order_by(ModelProvider.updated_at.desc())
    )
    active = result.scalar_one_or_none()

    if active is None:
        return Response(msg="未配置模型提供商", data=None)
    return Response(data=_to_provider_data(active))


@router.get("/provider/list")
async def list_providers(db: SessionDep) -> Response[list[ProviderData]]:
    """列出所有模型提供商配置。"""
    result = await db.execute(select(ModelProvider).order_by(ModelProvider.created_at.desc()))
    providers = result.scalars().all()
    return Response(data=[_to_provider_data(p) for p in providers])


@router.put("/provider/{provider_id}")
async def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    db: SessionDep,
) -> Response[ProviderData]:
    """更新模型提供商配置。

    只更新请求体中提供的字段，未提供的字段保持不变。
    """
    result = await db.execute(select(ModelProvider).where(ModelProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail=f"未找到提供商: {provider_id}")

    # 检查名称唯一性
    if body.name is not None and body.name != provider.name:
        existing = await db.execute(select(ModelProvider).where(ModelProvider.name == body.name))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail=f"提供商名称已存在: {body.name}")

    # 只更新提供的字段
    if body.name is not None:
        provider.name = body.name
    if body.model is not None:
        provider.model = body.model
    if body.base_url is not None:
        provider.base_url = body.base_url
    if body.api_key is not None:
        provider.api_key = body.api_key
    provider.updated_at = datetime.now()

    logger.info(f"[provider] 更新提供商: id={provider_id}")
    return Response(msg="模型提供商已更新", data=_to_provider_data(provider))


@router.put("/provider/{provider_id}/activate")
async def activate_provider(provider_id: int, db: SessionDep) -> Response[ProviderData]:
    """激活指定的模型提供商，同时停用其他所有提供商。"""
    result = await db.execute(select(ModelProvider).where(ModelProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail=f"未找到提供商: {provider_id}")

    # 将所有现有提供商设为非激活
    result = await db.execute(select(ModelProvider).where(ModelProvider.is_active.is_(True)))
    for old in result.scalars().all():
        old.is_active = False

    provider.is_active = True
    provider.updated_at = datetime.now()
    logger.info(f"[provider] 激活提供商: id={provider_id}, name={provider.name}")

    return Response(msg="模型提供商已激活", data=_to_provider_data(provider))


@router.delete("/provider/{provider_id}")
async def delete_provider(provider_id: int, db: SessionDep) -> Response[dict[str, Any]]:
    """删除模型提供商配置。

    如果删除的是激活的提供商，需要手动激活另一个。
    """
    result = await db.execute(select(ModelProvider).where(ModelProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail=f"未找到提供商: {provider_id}")

    was_active = provider.is_active
    await db.delete(provider)
    logger.info(f"[provider] 删除提供商: id={provider_id}, name={provider.name}")

    msg = "模型提供商已删除"
    if was_active:
        msg += "（注意：删除的是激活的提供商，请激活其他提供商）"

    return Response(msg=msg, data={"id": provider_id})


async def get_active_provider_config(db: AsyncSession) -> ModelProvider | None:
    """获取当前激活的模型提供商配置（供 judge 端点调用）。

    Returns:
        激活的 ModelProvider 对象，如果没有则返回 None。
    """
    result = await db.execute(
        select(ModelProvider).where(ModelProvider.is_active.is_(True)).order_by(ModelProvider.updated_at.desc())
    )
    return result.scalar_one_or_none()
