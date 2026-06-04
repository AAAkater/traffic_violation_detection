"""红绿灯检测器 — 从行车记录仪图像中检测、分类并提取红绿灯区域。"""

from detector.classifier import (
    classify_and_filter_back,
    classify_traffic_light,
    is_front_facing,
    is_vehicle_traffic_light,
)
from detector.filter import filter_spatial
from detector.merger import merge_nearby_boxes, merge_or_expand
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.pipeline import run
from detector.utils.image_tools import (
    crop_and_save_traffic_lights,
    save_quadrants,
    split_image_into_4,
)

__all__ = [
    "Detection",
    "TrafficLightDetector",
    "classify_and_filter_back",
    "classify_traffic_light",
    "crop_and_save_traffic_lights",
    "filter_spatial",
    "is_front_facing",
    "is_vehicle_traffic_light",
    "merge_nearby_boxes",
    "merge_or_expand",
    "run",
    "save_quadrants",
    "split_image_into_4",
]
