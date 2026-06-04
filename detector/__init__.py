"""红绿灯检测器 — 从行车记录仪图像中检测、分类并提取红绿灯区域。"""

from detector.classifier import (
    classify_and_filter_back,
    classify_traffic_light,
    is_front_facing,
    is_vehicle_traffic_light,
)
from detector.filter import filter_spatial
from detector.integrated_pipeline import run_pipeline
from detector.merger import merge_nearby_boxes, merge_or_expand
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.pipeline import run
from detector.settings import DetectionSettings, JudgeSettings, PipelineSettings
from detector.tasks.judge_task import JudgeResult, JudgeTask
from detector.utils.image_tools import (
    crop_and_save_traffic_lights,
    crop_upper_region,
    save_cropped_region,
    save_quadrants,
    split_image_into_4,
)

__all__ = [
    "Detection",
    "DetectionSettings",
    "JudgeResult",
    "JudgeSettings",
    "JudgeTask",
    "PipelineSettings",
    "TrafficLightDetector",
    "run_pipeline",
    "classify_and_filter_back",
    "classify_traffic_light",
    "crop_and_save_traffic_lights",
    "crop_upper_region",
    "filter_spatial",
    "is_front_facing",
    "is_vehicle_traffic_light",
    "merge_nearby_boxes",
    "merge_or_expand",
    "run",
    "save_cropped_region",
    "save_quadrants",
    "split_image_into_4",
]
