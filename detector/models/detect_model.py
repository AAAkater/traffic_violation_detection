"""红绿灯检测模型 — YOLO 加载、推理、空间过滤、画框标注。"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field
from ultralytics import YOLO

from detector.utils import logger

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 检测框颜色（按类别区分）
COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "off": (128, 128, 128),
    "wait_on": (255, 165, 0),
}


FONT = ImageFont.load_default()


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


class Detection(BaseModel):
    """单个红绿灯检测结果。"""

    bbox: list[float] = Field(description="[x1, y1, x2, y2] 边界框坐标")
    confidence: float = Field(description="检测置信度")
    class_name: str = Field(
        default="", description="类别名称，如 red/green/yellow/off/wait_on"
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


# ---------------------------------------------------------------------------
# 检测器
# ---------------------------------------------------------------------------


class TrafficLightDetector:
    """红绿灯检测器：YOLO 推理 + 空间过滤 + 画框标注。

    Args:
        model_path: YOLO 模型权重路径。
        conf_threshold: 检测置信度阈值。
        device: 推理设备，"cuda" / "cpu" / "cuda:0" 等，默认 None 让 YOLO 自动选择。
    """

    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.5,
        device: str | None = None,
    ) -> None:
        self._model = YOLO(model_path, verbose=False)
        self.conf_threshold = conf_threshold
        self._device = device

    # ── YOLO 推理 ──

    def detect(self, source: str | np.ndarray) -> list[Detection]:
        """检测图片中的红绿灯，返回检测结果列表。"""
        results = self._model.predict(source=source, verbose=False, device=self._device)
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

    # ── 空间过滤 ──

    def filter_spatial(
        self,
        detections: list[Detection],
        image_height: int,
        image_width: int,
        *,
        upper_ratio: float = 0.5,
        edge_ratio: float = 0.20,
        label: str = "",
    ) -> list[Detection]:
        """按空间位置过滤检测框：仅保留上半中间区域。

        Returns:
            过滤后保留的检测框。
        """
        cutoff_y = image_height * upper_ratio
        cutoff_x_left = image_width * edge_ratio
        cutoff_x_right = image_width * (1 - edge_ratio)

        kept: list[Detection] = []
        removed_lower = 0
        removed_edge = 0

        for d in detections:
            if d.center_y >= cutoff_y:
                removed_lower += 1
            elif d.center_x < cutoff_x_left or d.center_x > cutoff_x_right:
                removed_edge += 1
            else:
                kept.append(d)

        prefix = f"{label} " if label else ""
        if removed_lower:
            logger.debug(
                f"{prefix}剔除 {removed_lower} 个下半区域框, 保留 {len(kept)} 个"
            )
        if removed_edge:
            logger.debug(f"{prefix}剔除 {removed_edge} 个边缘框, 保留 {len(kept)} 个")

        return kept

    # ── 画框标注 ──

    def draw_detections(
        self,
        img: Image.Image,
        detections: list[Detection],
    ) -> Image.Image:
        """在图片上绘制检测框和类别标签，返回标注后的副本。"""
        annotated = img.copy()
        draw = ImageDraw.Draw(annotated)

        for det in detections:
            cls_name = det.class_name
            x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
            color = COLORS.get(cls_name, (255, 255, 255))

            draw.rectangle([x1, y1, x2, y2], outline=color, width=4)

            # 标签放在检测框下方
            text = cls_name
            text_x, text_y = x1, y2 + 2
            bbox = draw.textbbox((text_x + 4, text_y + 2), text, font=FONT)
            pad = 4
            draw.rectangle([text_x, text_y, bbox[2] + pad, bbox[3] + pad], fill=color)
            draw.text((text_x + 4, text_y + 2), text, fill=(255, 255, 255), font=FONT)

        return annotated
