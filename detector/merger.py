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


def merge_or_expand(
    detections: list[Detection],
    image_width: int,
    image_height: int,
    xy_distance_threshold: float = 200.0,
    expand_ratio: float = 0.125,
) -> list[Detection]:
    """智能合并或扩大。

    策略：
      1. 仅剩 1 个框 → 扩大：左右各扩 1/8 图宽、上下各扩 1/8 图高
      2. 剩余 2+ 个框 → 检查 y 范围是否有重叠（同一水平线），
         全部重叠 → 合并为外接矩形；有框不重叠 → 返回空，视为检测失败

    Args:
        detections: 检测结果列表。
        image_width: 图像宽度。
        image_height: 图像高度。
        xy_distance_threshold: 合并中心距离阈值（已废弃，保留接口兼容）。
        expand_ratio: 单框的扩展比例。

    Returns:
        处理后的检测结果列表。失败时返回空列表。
    """
    if len(detections) <= 1:
        return [
            expand_single_box(detections[0], image_width, image_height, expand_ratio)
        ]

    # 2+ 个框：检查是否全部在同一水平线上（y 范围有重叠）
    all_overlap = True
    for i in range(len(detections)):
        for j in range(i + 1, len(detections)):
            y_overlap = max(
                0,
                min(detections[i].y2, detections[j].y2)
                - max(detections[i].y1, detections[j].y1),
            )
            if y_overlap <= 0:
                all_overlap = False
                break
        if not all_overlap:
            break

    if not all_overlap:
        return []

    # 全部重叠 → 合并为外接矩形
    x1 = min(d.x1 for d in detections)
    y1 = min(d.y1 for d in detections)
    x2 = max(d.x2 for d in detections)
    y2 = max(d.y2 for d in detections)
    best_conf = max(d.confidence for d in detections)

    return [
        Detection(
            bbox=[x1, y1, x2, y2],
            confidence=round(best_conf, 3),
        )
    ]


def expand_single_box(
    detection: Detection,
    image_width: int,
    image_height: int,
    expand_ratio: float = 0.125,
) -> Detection:
    """当只检测到一个红绿灯时，左右各扩大 1/8 图像宽度、上下各扩大 1/8 图像高度。

    单个检测框很可能只框住了灯组中的一个灯（如绿灯），
    扩大后可以覆盖同一灯杆上的直行/左转/右转等所有灯。

    Args:
        detection: 单个检测结果。
        image_width: 图像宽度。
        image_height: 图像高度。
        expand_ratio: 每个方向的扩展比例（相对于图像尺寸），默认 1/8。

    Returns:
        扩大后的检测结果。
    """
    dx = int(image_width * expand_ratio)
    dy = int(image_height * expand_ratio)

    new_x1 = max(0, detection.x1 - dx)
    new_y1 = max(0, detection.y1 - dy)
    new_x2 = min(image_width, detection.x2 + dx)
    new_y2 = min(image_height, detection.y2 + dy)

    return Detection(
        bbox=[float(new_x1), float(new_y1), float(new_x2), float(new_y2)],
        confidence=detection.confidence,
    )
