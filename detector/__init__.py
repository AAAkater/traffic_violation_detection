"""红绿灯检测器 — 从行车记录仪图像中检测、提取红绿灯区域并画框标注。"""

from detector.detect import run
from detector.judge import JudgeResult, JudgeTask, run_judge
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.preprocess import preprocess
from detector.settings import Settings, settings

__all__ = [
    "Detection",
    "JudgeResult",
    "JudgeTask",
    "Settings",
    "TrafficLightDetector",
    "preprocess",
    "run",
    "run_judge",
    "settings",
]
