"""红绿灯检测器 — 从行车记录仪图像中检测、提取红绿灯区域并画框标注。"""

from detector.classifier import (
    classify_traffic_light,
    is_front_facing,
    is_vehicle_traffic_light,
)
from detector.filter import filter_spatial
from detector.integrated_pipeline import run_pipeline
from detector.merger import merge_nearby_boxes
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.pipeline import run
from detector.settings import DetectionSettings, JudgeSettings, PipelineSettings
from detector.tasks.judge_task import JudgeResult, JudgeTask

__all__ = [
    "Detection",
    "DetectionSettings",
    "JudgeResult",
    "JudgeSettings",
    "JudgeTask",
    "PipelineSettings",
    "TrafficLightDetector",
    "run_pipeline",
    "classify_traffic_light",
    "filter_spatial",
    "is_front_facing",
    "is_vehicle_traffic_light",
    "merge_nearby_boxes",
    "run",
]
