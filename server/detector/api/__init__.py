"""API 模块 — 提供 lifespan 与 v1 路由。"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from modelscope.hub.file_download import model_file_download

from detector.api.health import router as health_router
from detector.api.judge import router as judge_router
from detector.settings import settings
from detector.utils import logger

# ── v1 路由 ───────────────────────────────────────────────
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(judge_router)


def _ensure_model(model_path: str) -> None:
    """如果模型权重文件不存在，从 ModelScope 自动下载。"""
    path = Path(model_path)
    if path.is_file():
        logger.info(f"模型权重已存在: {model_path}")
        return

    logger.warning(f"模型权重不存在: {model_path}")
    slug = os.environ.get("MODELSCOPE_MODEL_SLUG", "AAAkater/tvd_yolo26")
    logger.info(f"正在从 ModelScope 下载: {slug}/{path.name} → {path.parent}")

    try:
        model_file_download(
            model_id=slug,
            file_path=path.name,
            cache_dir=str(path.parent),
            local_dir=str(path.parent),
        )
    except Exception as e:
        raise FileNotFoundError(
            f"无法下载模型权重 ({slug})，请检查网络或手动放置到 {path}。\n错误: {e}"
        ) from e

    logger.info(f"模型下载完成: {path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时打印全局配置并确保模型就绪。"""
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

    _ensure_model(settings.yolo_model_path)
    yield
