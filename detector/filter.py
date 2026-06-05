"""检测框空间过滤 — 按位置筛选红绿灯 bbox。"""

from __future__ import annotations

import numpy as np

from detector.models.detect_model import Detection
from detector.utils import logger


def filter_spatial(
    detections: list[Detection],
    image_height: int,
    image_width: int,
    image: np.ndarray | None = None,
    upper_ratio: float = 0.5,
    edge_ratio: float = 0.20,
    label: str = "",
) -> tuple[list[Detection], list[Detection], list[Detection]]:
    """按空间位置过滤检测框：上半区域 + 水平边缘。

    在行车记录仪画面中，红绿灯通常位于画面上方且不在水平边缘，
    下半区域或左右边缘的检测框往往是背面、行人灯或误检。

    Args:
        detections: 检测结果列表。
        image_height: 图片高度（像素）。
        image_width: 图片宽度（像素）。
        image: 原始图像（BGR 格式），当前未使用，保留参数以兼容调用方。
        upper_ratio: 判定"上部"的占比线，默认 0.5 即上半 50%。
        edge_ratio: 水平边缘剔除比例，默认 0.20 即左右各 20%。
        label: 日志前缀，如 "[image_stem][q_name]"。

    Returns:
        (kept, removed_lower, removed_edge): 保留的检测框 + 下半区域剔除 + 边缘剔除。
    """
    cutoff_y = image_height * upper_ratio
    cutoff_x_left = image_width * edge_ratio
    cutoff_x_right = image_width * (1 - edge_ratio)

    kept: list[Detection] = []
    removed_lower: list[Detection] = []
    removed_edge: list[Detection] = []

    for d in detections:
        if d.center_y >= cutoff_y:
            removed_lower.append(d)
        elif d.center_x < cutoff_x_left or d.center_x > cutoff_x_right:
            removed_edge.append(d)
        else:
            kept.append(d)

    prefix_log = f"{label} " if label else ""
    if removed_lower:
        logger.debug(
            f"{prefix_log}剔除 {len(removed_lower)} 个下半区域框, 保留 {len(kept)} 个"
        )
    if removed_edge:
        logger.debug(
            f"{prefix_log}剔除 {len(removed_edge)} 个边缘框(疑似行人灯), "
            f"保留 {len(kept)} 个中间区域"
        )

    return kept, removed_lower, removed_edge
