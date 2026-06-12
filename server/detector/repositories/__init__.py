"""数据访问层 — Repository 模式封装数据库操作。"""

from detector.repositories.detect import DetectImageRepo, DetectionBoxRepo
from detector.repositories.judge import JudgeRecordRepo
from detector.repositories.prompt import SystemPromptRepo
from detector.repositories.provider import ModelProviderRepo

__all__ = [
    "DetectImageRepo",
    "DetectionBoxRepo",
    "JudgeRecordRepo",
    "SystemPromptRepo",
    "ModelProviderRepo",
]
