"""数据库与存储模块 — PostgreSQL 引擎 + S3 对象存储 + ORM 表定义。"""

from detector.db.engine import Base, async_session, engine, get_db
from detector.db.storage import download_image, upload_bytes, upload_pil_image
from detector.db.tables import DetectImage, DetectionBox, JudgeRecord, SystemPrompt

__all__ = [
    # engine
    "Base",
    "engine",
    "async_session",
    "get_db",
    # storage
    "download_image",
    "upload_bytes",
    "upload_pil_image",
    # tables
    "SystemPrompt",
    "DetectImage",
    "DetectionBox",
    "JudgeRecord",
]
