"""保存工具 — 裁剪并保存检测到的红绿灯区域和子图。"""

from pathlib import Path

import cv2
import numpy as np

from detector.classifier import classify_traffic_light
from detector.utils import logger


def crop_and_save_traffic_lights(
    image: np.ndarray,
    detections: list[dict],
    output_dir: str = "./output/crops",
    prefix: str = "traffic_light",
    skip_back_side: bool = True,
    skip_pedestrian: bool = False,
) -> list[str]:
    """根据检测结果裁剪红绿灯区域并保存到文件。

    Args:
        image: 原始图像（BGR 格式 numpy 数组）。
        detections: detect_traffic_lights 返回的检测结果列表。
        output_dir: 裁剪图片输出目录。
        prefix: 输出文件名前缀。
        skip_back_side: 是否跳过背面红绿灯，仅保存正面。
        skip_pedestrian: 是否跳过行人交通灯，仅保存机动车灯。

    Returns:
        保存的文件路径列表。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    front_count = 0

    for i, det in enumerate(detections):
        x1, y1, x2, y2 = map(int, det["bbox"])
        crop = image[y1:y2, x1:x2]

        if skip_back_side or skip_pedestrian:
            label = classify_traffic_light(crop)
            if label == "back" and skip_back_side:
                logger.info(f"[跳过] 第 {i + 1} 个为背面红绿灯，不保存。")
                continue
            if label == "pedestrian" and skip_pedestrian:
                logger.info(f"[跳过] 第 {i + 1} 个为行人交通灯，不保存。")
                continue

        front_count += 1
        filename = f"{prefix}_{front_count:02d}_conf{det['confidence']:.2f}.jpg"
        filepath = output_path / filename
        cv2.imwrite(str(filepath), crop)
        saved_files.append(str(filepath))
        logger.debug(f"已保存正面裁剪区域: {filepath}")

    return saved_files


def save_quadrants(
    quadrants: list[tuple[str, np.ndarray]],
    output_dir: str = "./output/quadrants",
) -> list[str]:
    """将分割后的四个子图保存到文件。

    Args:
        quadrants: split_image_into_4 返回的 [(区域名, 子图数组), ...]。
        output_dir: 输出目录。

    Returns:
        保存的四张子图路径列表。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for name, sub_img in quadrants:
        filepath = output_path / f"quadrant_{name}.jpg"
        cv2.imwrite(str(filepath), sub_img)
        saved.append(str(filepath))
        logger.debug(f"已保存子图 [{name}]: {filepath}")

    return saved
