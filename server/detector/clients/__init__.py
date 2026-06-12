"""外部客户端 — YOLO 检测器与视觉 LLM 客户端。"""

from detector.clients.vision import VisionClient
from detector.clients.yolo import TrafficLightDetector

__all__ = [
    "TrafficLightDetector",
    "VisionClient",
]
