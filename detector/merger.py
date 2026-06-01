"""bbox 合并 — 将同一灯杆上相邻的红绿灯检测框合并为一组。"""

import numpy as np


def merge_nearby_boxes(
    detections: list[dict],
    xy_distance_threshold: float = 200.0,
) -> list[dict]:
    """合并空间上相近的红绿灯 bbox（同一灯杆的一组灯）。

    同一灯杆上的红绿灯（直行、左转、右转等）在画面上紧挨着排列。
    当两个 bbox 中心点距离小于阈值时予以合并，取外接矩形，
    置信度取组内最大值。

    Args:
        detections: 检测结果列表。
        xy_distance_threshold: bbox 中心点之间的欧氏距离阈值（像素）。

    Returns:
        合并后的检测结果列表，每组一条。额外字段:
          - "merged_from": 参与合并的原始检测框数量。
    """
    if len(detections) <= 1:
        return [{**d, "merged_from": 1} for d in detections]

    # 先按置信度降序排列，确保合并到置信度最高的组
    items = sorted(detections, key=lambda d: d["confidence"], reverse=True)
    merged: list[dict] = []

    used = [False] * len(items)

    for i in range(len(items)):
        if used[i]:
            continue

        bbox_i = items[i]["bbox"]
        cx_i = (bbox_i[0] + bbox_i[2]) / 2
        cy_i = (bbox_i[1] + bbox_i[3]) / 2
        best_conf = items[i]["confidence"]

        x1, y1, x2, y2 = bbox_i
        count = 1  # 参与合并的原始检测框数

        for j in range(i + 1, len(items)):
            if used[j]:
                continue

            bbox_j = items[j]["bbox"]
            cx_j = (bbox_j[0] + bbox_j[2]) / 2
            cy_j = (bbox_j[1] + bbox_j[3]) / 2

            dist = np.sqrt((cx_i - cx_j) ** 2 + (cy_i - cy_j) ** 2)

            if dist < xy_distance_threshold:
                used[j] = True
                count += 1
                x1 = min(x1, bbox_j[0])
                y1 = min(y1, bbox_j[1])
                x2 = max(x2, bbox_j[2])
                y2 = max(y2, bbox_j[3])
                if items[j]["confidence"] > best_conf:
                    best_conf = items[j]["confidence"]

        merged.append(
            {
                "bbox": [x1, y1, x2, y2],
                "confidence": round(best_conf, 3),
                "merged_from": count,
            }
        )
        used[i] = True

    return merged


def merge_or_expand(
    detections: list[dict],
    image_width: int,
    image_height: int,
    xy_distance_threshold: float = 200.0,
    expand_ratio: float = 0.125,
) -> list[dict]:
    """智能合并或扩大：合并近距离的检测框，对无法合并的单个框做扩大。

    策略：
      1. 先按中心距离合并（merge_nearby_boxes）
      2. 对于 merged_from==1（合并失败的单飞框），左右各扩 1/8 图宽、上下各扩 1/8 图高
      3. 对于 merged_from>=2（合并成功的组），保持不动

    Args:
        detections: 检测结果列表。
        image_width: 图像宽度。
        image_height: 图像高度。
        xy_distance_threshold: 合并中心距离阈值。
        expand_ratio: 单飞框的扩展比例。

    Returns:
        处理后的检测结果列表。不包含 merged_from 内部字段。
    """
    if len(detections) <= 1:
        return [
            expand_single_box(detections[0], image_width, image_height, expand_ratio)
        ]

    merged_groups = merge_nearby_boxes(detections, xy_distance_threshold)

    result: list[dict] = []
    for group in merged_groups:
        count = group.pop("merged_from", 1)
        if count == 1:
            result.append(
                expand_single_box(group, image_width, image_height, expand_ratio)
            )
        else:
            result.append(group)

    return result


def expand_single_box(
    detection: dict,
    image_width: int,
    image_height: int,
    expand_ratio: float = 0.125,
) -> dict:
    """当只检测到一个红绿灯时，左右各扩大 1/8 图像宽度、上下各扩大 1/8 图像高度。

    单个检测框很可能只框住了灯组中的一个灯（如绿灯），
    扩大后可以覆盖同一灯杆上的直行/左转/右转等所有灯。

    Args:
        detection: 单个检测结果 {"bbox": [x1, y1, x2, y2], "confidence": ...}。
        image_width: 图像宽度。
        image_height: 图像高度。
        expand_ratio: 每个方向的扩展比例（相对于图像尺寸），默认 1/8。

    Returns:
        扩大后的检测结果。
    """
    x1, y1, x2, y2 = detection["bbox"]

    dx = int(image_width * expand_ratio)
    dy = int(image_height * expand_ratio)

    x1 = max(0, x1 - dx)
    y1 = max(0, y1 - dy)
    x2 = min(image_width, x2 + dx)
    y2 = min(image_height, y2 + dy)

    return {
        "bbox": [float(x1), float(y1), float(x2), float(y2)],
        "confidence": detection["confidence"],
    }
