"""数据库与存储模块 — PostgreSQL 引擎 + S3 对象存储 + ORM 表定义。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from detector.clients.yolo import TrafficLightDetector
from detector.db.engine import Base, async_session, db_engine, get_db
from detector.db.storage import S3Storage, s3_storage
from detector.db.tables import DetectImage, DetectionBox, JudgeRecord, ModelProvider, SystemPrompt
from detector.settings import settings
from detector.utils import logger

__all__ = [
    # engine
    "Base",
    "db_engine",
    "async_session",
    "get_db",
    # storage
    "S3Storage",
    "s3_storage",
    # tables
    "SystemPrompt",
    "ModelProvider",
    "DetectImage",
    "DetectionBox",
    "JudgeRecord",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时打印全局配置并确保模型就绪。"""
    logger.info("=" * 50)
    logger.info("加载全局配置 Settings:")
    logger.info(f"  yolo_model_path    = {settings.YOLO_MODEL_PATH!r}")
    logger.info(f"  yolo_conf_threshold = {settings.YOLO_CONF_THRESHOLD}")
    logger.info(f"  yolo_device         = {settings.YOLO_DEVICE!r}")
    logger.info("  模型提供商配置: 通过 /v1/provider 接口管理")
    logger.info("=" * 50)

    TrafficLightDetector.ensure_model(settings.YOLO_MODEL_PATH)

    s3_storage.ensure_bucket(settings.S3_BUCKET_NAME)
    logger.info(f"[storage] S3Storage 已初始化: endpoint={settings.S3_ENDPOINT!r}, bucket={settings.S3_BUCKET_NAME}")

    # 创建数据库表（如果不存在）
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表检查完成")

    yield
