"""健康检查端点。"""

from fastapi import APIRouter

from detector.common.response import Response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> Response[None]:
    """健康检查端点（供 Docker healthcheck 使用）。"""
    return Response(data=None)
