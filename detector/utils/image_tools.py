"""图片工具 — 分割、保存子图等图像处理辅助函数。"""

from pathlib import Path

import cv2
import numpy as np

from detector.models.detect_model import Detection
from detector.utils import logger


def split_image_into_4(image_path: str) -> list[tuple[str, np.ndarray]]:
    """将大图按宽高中点均分为 4 个子图（2×2 分割）。

    Args:
        image_path: 输入图片路径。

    Returns:
        [(区域名, 子图数组), ...] 顺序：左上 → 右上 → 左下 → 右下。
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")

    h, w = img.shape[:2]
    mid_h, mid_w = h // 2, w // 2

    quadrants = [
        ("左上", img[0:mid_h, 0:mid_w]),
        ("右上", img[0:mid_h, mid_w:w]),
        ("左下", img[mid_h:h, 0:mid_w]),
        ("右下", img[mid_h:h, mid_w:w]),
    ]
    return quadrants


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


def crop_and_save_traffic_lights(
    image: np.ndarray,
    detections: list[Detection],
    output_dir: str = "./output/crops",
    prefix: str = "traffic_light",
) -> list[str]:
    """根据检测结果裁剪红绿灯区域并保存到文件。

    Args:
        image: 原始图像（BGR 格式 numpy 数组）。
        detections: 检测结果列表。
        output_dir: 裁剪图片输出目录。
        prefix: 输出文件名前缀。

    Returns:
        保存的文件路径列表。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []

    for i, det in enumerate(detections):
        x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
        crop = image[y1:y2, x1:x2]

        filename = f"{prefix}_{i + 1:02d}_conf{det.confidence:.2f}.jpg"
        filepath = output_path / filename
        cv2.imwrite(str(filepath), crop)
        saved_files.append(str(filepath))
        logger.debug(f"已保存裁剪区域: {filepath}")

    return saved_files
