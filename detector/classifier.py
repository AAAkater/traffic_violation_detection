"""正面/背面分类器 — 基于 HSV 颜色分析判断红绿灯朝向。

正面红绿灯有红/黄/绿三色灯盘，彩色像素占比高且纹理丰富；
背面为暗色金属壳体，几乎没有彩色像素，纹理单调。
"""

import cv2
import numpy as np

from detector.utils import logger


def is_front_facing(
    crop: np.ndarray,
    color_ratio_threshold: float = 0.01,
    min_texture_variance: float = 100.0,
    max_dark_ratio: float = 0.90,
) -> bool:
    """判断裁剪出的红绿灯区域是正面还是背面。

    三个条件必须**全部**满足才判定为正面：
      1. 红/黄/绿色像素占比 > color_ratio_threshold
      2. 灰度纹理方差 > min_texture_variance
      3. 低饱和暗色像素占比 < max_dark_ratio（背面几乎全是暗灰）

    Args:
        crop: 裁剪后的红绿灯图像（BGR 格式）。
        color_ratio_threshold: 彩色像素占比下限。
        min_texture_variance: 纹理方差下限。
        max_dark_ratio: 低饱和暗色像素占比上限，超过此值视为背面。

    Returns:
        True 表示正面，False 表示背面。
    """
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    # ---- 彩色像素占比 ----
    # 放宽饱和度下限（30），红灯/黄灯在较暗时饱和度偏低
    lower_red1 = np.array([0, 30, 40])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 30, 40])
    upper_red2 = np.array([180, 255, 255])
    lower_yellow = np.array([20, 30, 40])
    upper_yellow = np.array([35, 255, 255])
    lower_green = np.array([36, 30, 40])
    upper_green = np.array([85, 255, 255])

    mask_red1: np.ndarray = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2: np.ndarray = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_yellow: np.ndarray = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_green: np.ndarray = cv2.inRange(hsv, lower_green, upper_green)

    colored_mask: np.ndarray = mask_red1 | mask_red2 | mask_yellow | mask_green
    total_pixels = colored_mask.size
    color_ratio = np.count_nonzero(colored_mask) / total_pixels

    # 各颜色单独占比（用于调试）
    red_ratio = (
        np.count_nonzero(mask_red1) + np.count_nonzero(mask_red2)
    ) / total_pixels
    yellow_ratio = np.count_nonzero(mask_yellow) / total_pixels
    green_ratio = np.count_nonzero(mask_green) / total_pixels

    # ---- 暗色/低饱和像素占比（背面特征） ----
    lower_dark = np.array([0, 0, 0])
    upper_dark = np.array([180, 50, 180])  # 饱和度 < 50，亮度 < 180
    dark_mask: np.ndarray = cv2.inRange(hsv, lower_dark, upper_dark)
    dark_ratio = np.count_nonzero(dark_mask) / dark_mask.size

    # ---- 纹理方差 ----
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    texture_variance = float(np.var(gray))

    is_front = bool(
        (color_ratio > color_ratio_threshold)
        and (texture_variance > min_texture_variance)
        and (dark_ratio < max_dark_ratio)
    )

    logger.debug(
        f"[正/背面判定] {'FRONT' if is_front else 'BACK'} "
        f"总彩色={color_ratio:.4f} "
        f"红={red_ratio:.4f} 黄={yellow_ratio:.4f} 绿={green_ratio:.4f} "
        f"暗色={dark_ratio:.3f} 纹理={texture_variance:.1f}"
    )

    return is_front
