"""健康检查端点。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """健康检查端点（供 Docker healthcheck 使用）。"""
    return {"status": "ok"}
