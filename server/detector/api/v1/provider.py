"""模型提供商端点 — 管理 LLM 判定模型的连接配置。

用户通过此接口增删改查模型提供商配置，并列出提供商下的可用模型。
"""

from fastapi import APIRouter, HTTPException

from detector.api.dep import ProviderServiceDep
from detector.models.provider import (
    ModelActivateRequest,
    ModelDeactivateRequest,
    ProviderCreate,
    ProviderData,
    ProviderModelsData,
    ProviderUpdate,
)
from detector.models.response import Response

router = APIRouter(tags=["provider"])


@router.post("/provider")
async def create_provider(body: ProviderCreate, service: ProviderServiceDep) -> Response[ProviderData]:
    """创建模型提供商配置。"""
    try:
        data = await service.create_provider(body)
        return Response(msg="模型提供商已创建", data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/provider/list")
async def list_providers(service: ProviderServiceDep) -> Response[list[ProviderData]]:
    """列出所有模型提供商配置。"""
    data = await service.list_providers()
    return Response(data=data)


@router.get("/provider/{provider_id}")
async def get_provider(provider_id: int, service: ProviderServiceDep) -> Response[ProviderData]:
    """获取指定 ID 的模型提供商配置。"""
    data = await service.get_provider(provider_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"未找到提供商: {provider_id}")
    return Response(data=data)


@router.get("/provider/{provider_id}/models")
async def list_provider_models(provider_id: int, service: ProviderServiceDep) -> Response[ProviderModelsData]:
    """列出指定提供商的所有可用模型。

    通过 OpenAI SDK 的 list models 接口获取模型信息。
    """
    try:
        data = await service.list_models(provider_id)
        return Response(data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/provider/{provider_id}/activated-models")
async def list_activated_models(provider_id: int, service: ProviderServiceDep) -> Response[list[str]]:
    """获取指定提供商的所有已激活模型名称。"""
    try:
        data = await service.list_activated_models(provider_id)
        return Response(data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/provider/{provider_id}/activate-model")
async def activate_model(
    provider_id: int,
    body: ModelActivateRequest,
    service: ProviderServiceDep,
) -> Response[ProviderData]:
    """激活指定提供商的某个模型。"""
    try:
        data = await service.activate_model(provider_id, body.model)
        return Response(msg=f"模型 {body.model} 已激活", data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/provider/{provider_id}/deactivate-model")
async def deactivate_model(
    provider_id: int,
    body: ModelDeactivateRequest,
    service: ProviderServiceDep,
) -> Response[ProviderData]:
    """停用指定提供商的某个模型。"""
    try:
        data = await service.deactivate_model(provider_id, body.model)
        return Response(msg=f"模型 {body.model} 已停用", data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/provider/update")
async def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    service: ProviderServiceDep,
) -> Response[ProviderData]:
    """更新模型提供商配置。

    只更新请求体中提供的字段，未提供的字段保持不变。
    """
    try:
        data = await service.update_provider(provider_id, body)
        return Response(msg="模型提供商已更新", data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/provider/delete")
async def delete_provider(provider_id: int, service: ProviderServiceDep) -> Response[dict]:
    """删除模型提供商配置。"""
    try:
        data = await service.delete_provider(provider_id)
        return Response(msg=data["msg"], data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
