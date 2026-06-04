"""红绿灯检测模型 — 封装 YOLO 模型的加载与推理。"""

import numpy as np
from pydantic import BaseModel, Field
from ultralytics import YOLO

# YOLO COCO 数据集中红绿灯的类别 ID
TRAFFIC_LIGHT_CLASS = 9


class Detection(BaseModel):
    """单个红绿灯检测结果。"""

    bbox: list[float] = Field(description="[x1, y1, x2, y2] 边界框坐标")
    confidence: float = Field(description="检测置信度")
    merged_from: int | None = Field(
        default=None, description="参与合并的原始检测框数量"
    )

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

    def shift(self, dx: float = 0, dy: float = 0) -> "Detection":
        """返回坐标偏移后的新 Detection 实例。

        用于将裁剪区域内的检测坐标映射回原图坐标。

        Args:
            dx: X 方向偏移量（像素）。
            dy: Y 方向偏移量（像素）。

        Returns:
            偏移后的新 Detection 实例。
        """
        return self.model_copy(
            update={
                "bbox": [
                    self.bbox[0] + dx,
                    self.bbox[1] + dy,
                    self.bbox[2] + dx,
                    self.bbox[3] + dy,
                ]
            }
        )


class TrafficLightDetector:
    """红绿灯检测器，封装 YOLO 模型的加载与推理。

    Args:
        model_path: YOLO 模型权重路径。
        conf_threshold: 检测置信度阈值，低于此值的结果将被过滤。
    """

    def __init__(self, model_path: str, conf_threshold: float = 0.5) -> None:
        self._model = YOLO(model_path, verbose=False)
        self.conf_threshold = conf_threshold

    def detect(self, source: str | np.ndarray) -> list[Detection]:
        """检测图片中的红绿灯，返回检测结果列表。

        可接受文件路径或 numpy 数组（BGR 格式）作为输入。

        Args:
            source: 图片路径或 numpy 数组。

        Returns:
            检测结果列表，每个元素为 Detection 实例。
        """
        results = self._model.predict(
            source=source, classes=[TRAFFIC_LIGHT_CLASS], verbose=False
        )
        detections: list[Detection] = []

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                conf = box.conf.item()
                if conf < self.conf_threshold:
                    continue
                detections.append(
                    Detection(
                        bbox=box.xyxy.tolist()[0],
                        confidence=round(conf, 3),
                    )
                )

        return detections

    def has_traffic_light(self, source: str | np.ndarray) -> bool:
        """判断图片中是否包含红绿灯。

        Args:
            source: 图片路径或 numpy 数组。

        Returns:
            True 表示图片中有红绿灯，False 表示没有。
        """
        return len(self.detect(source)) > 0
