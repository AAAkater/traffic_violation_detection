"""API 模块 — 提供 lifespan 与 v1 路由。"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from modelscope.hub.file_download import model_file_download

from detector.api.detect import router as detect_router
from detector.api.health import router as health_router
from detector.api.history import router as history_router
from detector.api.judge import router as judge_router
from detector.api.prompt import router as prompt_router
from detector.api.provider import router as provider_router
from detector.db import Base, db_engine
from detector.db.storage import s3_storage
from detector.settings import settings
from detector.utils import logger

# ── v1 路由 ───────────────────────────────────────────────
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(detect_router)
v1_router.include_router(prompt_router)
v1_router.include_router(provider_router)
v1_router.include_router(judge_router)
v1_router.include_router(history_router)


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
        raise FileNotFoundError(f"无法下载模型权重 ({slug})，请检查网络或手动放置到 {path}。\n错误: {e}") from e

    logger.info(f"模型下载完成: {path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时打印全局配置并确保模型就绪。"""
    logger.info("=" * 50)
    logger.info("加载全局配置 Settings:")
    logger.info(f"  yolo_model_path    = {settings.yolo_model_path!r}")
    logger.info(f"  yolo_conf_threshold = {settings.yolo_conf_threshold}")
    logger.info(f"  yolo_device         = {settings.yolo_device!r}")
    logger.info("  模型提供商配置: 通过 /v1/provider 接口管理")
    logger.info("=" * 50)

    _ensure_model(settings.yolo_model_path)

    s3_storage.ensure_bucket(settings.s3_bucket)
    logger.info(f"[storage] S3Storage 已初始化: endpoint={settings.s3_endpoint!r}, bucket={settings.s3_bucket!r}")

    # 创建数据库表（如果不存在）
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表检查完成")

    yield
