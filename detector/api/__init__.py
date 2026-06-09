"""API 模块 — 提供 lifespan 与 v1 路由。"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from detector.api.health import router as health_router
from detector.api.judge import router as judge_router
from detector.settings import settings
from detector.utils import logger

# ── v1 路由 ───────────────────────────────────────────────
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(judge_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时打印全局配置。"""
    logger.info("=" * 50)
    logger.info("加载全局配置 Settings:")
    logger.info(f"  yolo_model_path    = {settings.yolo_model_path!r}")
    logger.info(f"  yolo_conf_threshold = {settings.yolo_conf_threshold}")
    logger.info(f"  yolo_device         = {settings.yolo_device!r}")
    logger.info(f"  judge_model        = {settings.judge_model!r}")
    logger.info(f"  judge_base_url     = {settings.judge_base_url!r}")
    logger.info(
        f"  judge_api_key      = {'***' if settings.judge_api_key else '(empty)'}"
    )
    logger.info("=" * 50)
    yield
