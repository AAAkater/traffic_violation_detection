"""红绿灯检测器 — 从行车记录仪图像中检测、分类并提取红绿灯区域。"""

from detector.classifier import is_front_facing
from detector.detection import detect_traffic_lights, has_traffic_light
from detector.filter import filter_upper_region
from detector.merger import merge_nearby_boxes, merge_or_expand
from detector.pipeline import run
from detector.saver import crop_and_save_traffic_lights, save_quadrants
from detector.splitter import split_image_into_4

__all__ = [
    "crop_and_save_traffic_lights",
    "detect_traffic_lights",
    "filter_upper_region",
    "has_traffic_light",
    "is_front_facing",
    "merge_nearby_boxes",
    "merge_or_expand",
    "run",
    "save_quadrants",
    "split_image_into_4",
]
