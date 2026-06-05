"""bbox 合并 — 将同一灯杆上相邻的红绿灯检测框合并为一组。"""

from __future__ import annotations

import numpy as np

from detector.models.detect_model import Detection


def merge_nearby_boxes(
    detections: list[Detection],
    xy_distance_threshold: float = 200.0,
) -> list[Detection]:
    """合并空间上相近的红绿灯 bbox（同一灯杆的一组灯）。

    同一灯杆上的红绿灯（直行、左转、右转等）在画面上紧挨着排列。
    当两个 bbox 中心点距离小于阈值时予以合并，取外接矩形，
    置信度取组内最大值。

    Args:
        detections: 检测结果列表。
        xy_distance_threshold: bbox 中心点之间的欧氏距离阈值（像素）。

    Returns:
        合并后的检测结果列表，每组一条。额外字段:
          - merged_from: 参与合并的原始检测框数量。
    """
    if len(detections) <= 1:
        return [d.model_copy(update={"merged_from": 1}) for d in detections]

    # 先按置信度降序排列，确保合并到置信度最高的组
    items = sorted(detections, key=lambda d: d.confidence, reverse=True)
    merged: list[Detection] = []

    used = [False] * len(items)

    for i in range(len(items)):
        if used[i]:
            continue

        cx_i = items[i].center_x
        cy_i = items[i].center_y
        best_conf = items[i].confidence

        x1, y1, x2, y2 = items[i].x1, items[i].y1, items[i].x2, items[i].y2
        count = 1  # 参与合并的原始检测框数

        for j in range(i + 1, len(items)):
            if used[j]:
                continue

            cx_j = items[j].center_x
            cy_j = items[j].center_y

            dist = np.sqrt((cx_i - cx_j) ** 2 + (cy_i - cy_j) ** 2)

            if dist < xy_distance_threshold:
                used[j] = True
                count += 1
                x1 = min(x1, items[j].x1)
                y1 = min(y1, items[j].y1)
                x2 = max(x2, items[j].x2)
                y2 = max(y2, items[j].y2)
                if items[j].confidence > best_conf:
                    best_conf = items[j].confidence

        merged.append(
            Detection(
                bbox=[x1, y1, x2, y2],
                confidence=round(best_conf, 3),
                merged_from=count,
            )
        )
        used[i] = True

    return merged
