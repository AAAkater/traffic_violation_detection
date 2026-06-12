"""v1 API 路由 — 聚合所有 v1 版本端点。"""

from fastapi import APIRouter

from detector.api.v1.detect import router as detect_router
from detector.api.v1.health import router as health_router
from detector.api.v1.history import router as history_router
from detector.api.v1.judge import router as judge_router
from detector.api.v1.prompt import router as prompt_router
from detector.api.v1.provider import router as provider_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(health_router)
v1_router.include_router(detect_router)
v1_router.include_router(prompt_router)
v1_router.include_router(provider_router)
v1_router.include_router(judge_router)
v1_router.include_router(history_router)
