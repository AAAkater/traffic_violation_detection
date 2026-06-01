"""图片分割工具 — 将大图按 2×2 均分为 4 个子图。"""

import cv2
import numpy as np


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
