"""系统提示词端点 — 自定义 LLM 判定时使用的系统提示词，持久化到数据库。"""

from fastapi import APIRouter, HTTPException

from detector.api.dep import PromptServiceDep
from detector.models.prompt import PromptData, PromptListItem
from detector.models.response import Response

router = APIRouter(tags=["prompt"])


@router.post("/prompt")
async def set_prompt(name: str, content: str, service: PromptServiceDep) -> Response[PromptData]:
    """创建或更新系统提示词，并设为激活。

    Args:
        name: 提示词名称（唯一标识）。
        content: 提示词内容。
        service: 提示词管理服务。
    """
    try:
        data = await service.set_prompt(name=name, content=content)
        return Response(msg="系统提示词已更新", data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt")
async def get_prompt(service: PromptServiceDep) -> Response[PromptData]:
    """获取当前激活的系统提示词。"""
    data = await service.get_active_prompt()
    return Response(data=data)


@router.get("/prompt/list")
async def list_prompts(service: PromptServiceDep) -> Response[list[PromptListItem]]:
    """列出所有系统提示词。"""
    data = await service.list_prompts()
    return Response(data=data)
