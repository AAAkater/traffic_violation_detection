"""上传历史查询端点 — 分页查询检测记录，包含图片链接、LLM 回复、检测框坐标。"""

from fastapi import APIRouter, Query

from detector.api.dep import HistoryServiceDep
from detector.models.history import HistoryPage
from detector.models.response import Response

router = APIRouter(tags=["history"])


@router.get("/history")
async def get_history(
    service: HistoryServiceDep,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
) -> Response[HistoryPage]:
    """分页查询上传历史，包含图片链接、检测框坐标和 LLM 判定结果。"""
    data = await service.get_history(page=page, page_size=page_size)
    return Response(data=data)
