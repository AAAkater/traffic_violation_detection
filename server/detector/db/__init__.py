"""数据库与存储模块 — PostgreSQL 引擎 + S3 对象存储 + ORM 表定义。"""

from detector.db.engine import Base, SessionDep, async_session, db_engine, get_db
from detector.db.storage import S3Storage, s3_storage
from detector.db.tables import DetectImage, DetectionBox, JudgeRecord, ModelProvider, SystemPrompt

__all__ = [
    # engine
    "Base",
    "db_engine",
    "async_session",
    "get_db",
    "SessionDep",
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
