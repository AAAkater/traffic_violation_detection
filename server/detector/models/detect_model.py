"""红绿灯检测模型 — YOLO 加载与推理。"""

import time

import numpy as np
from pydantic import BaseModel, Field
from ultralytics import YOLO

from detector.utils import logger

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


class Detection(BaseModel):
    """单个红绿灯检测结果。"""

    bbox: list[float] = Field(description="[x1, y1, x2, y2] 边界框坐标")
    confidence: float = Field(description="检测置信度")
    class_name: str = Field(default="", description="类别名称，如 red/green/yellow/off/wait_on")

    @property
    def x1(self) -> float:
        return self.bbox[0]

    @property
    def y1(self) -> float:
        return self.bbox[1]

    @property
    def x2(self) -> float:
        return self.bbox[2]

    @property
    def y2(self) -> float:
        return self.bbox[3]

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


# ---------------------------------------------------------------------------
# 检测器
# ---------------------------------------------------------------------------


class TrafficLightDetector:
    """红绿灯检测器：YOLO 模型加载与推理。

    Args:
        model_path: YOLO 模型权重路径。
        conf_threshold: 检测置信度阈值。
        device: 推理设备，"cuda" / "cpu" / "cuda:0" 等。
    """

    def __init__(
        self,
        model_path: str,
        device: str,
        conf_threshold: float = 0.5,
    ) -> None:
        self._device = device
        self._model = YOLO(model_path, verbose=False).to(device)
        self.conf_threshold = conf_threshold

    def detect(self, source: str | np.ndarray) -> list[Detection]:
        """检测图片中的红绿灯，返回检测结果列表。"""
        t0 = time.perf_counter()
        results = self._model.predict(source=source, verbose=False, device=self._device)
        elapsed = time.perf_counter() - t0
        logger.info(f"[YOLO] 推理耗时: {elapsed:.3f}s")
        detections: list[Detection] = []

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                conf = box.conf.item()
                if conf < self.conf_threshold:
                    continue
                cls_id = int(box.cls.item())
                cls_name = self._model.names.get(cls_id, str(cls_id))
                detections.append(
                    Detection(
                        bbox=box.xyxy.tolist()[0],
                        confidence=round(conf, 3),
                        class_name=cls_name,
                    )
                )

        return detections
