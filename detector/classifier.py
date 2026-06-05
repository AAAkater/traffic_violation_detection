"""正面/背面/行人灯分类器 — 基于 HSV + 形状分析判断红绿灯类型。

正面机动车灯：红/黄/绿三色圆形灯盘，横向宽，彩色像素占比高且纹理丰富；
行人交通灯：纵向高窄，有人形图标/数字倒计时特征，彩色占比低；
背面：暗色金属壳体，几乎没有彩色像素，纹理单调。
"""

import cv2
import numpy as np

from detector.models.detect_model import Detection
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


def is_vehicle_traffic_light(
    crop: np.ndarray,
    min_aspect_ratio: float = 0.3,
    min_bright_spots: int = 2,
    min_colored_ratio: float = 0.008,
) -> bool:
    """判断是否是机动车交通灯（排除行人交通灯）。

    机动车灯 vs 行人灯的核心差异：
      - 宽高比：机动车灯横向宽 (w/h 大)，行人灯纵向高窄 (w/h 小)
      - 亮斑形态：机动车灯有 2~3 个圆形亮斑，行人灯是异形图标
      - 颜色分布：机动车灯红/黄/绿三色带状分布，行人灯仅红或绿单色为主

    Args:
        crop: 裁剪后的红绿灯图像（BGR 格式）。
        min_aspect_ratio: 最小宽高比，低于此值判定为行人灯。
        min_bright_spots: 最少亮斑数，低于此值可能是行人灯。
        min_colored_ratio: 最低彩色像素占比。

    Returns:
        True 表示机动车灯，False 表示可能是行人灯。
    """
    h, w = crop.shape[:2]
    if h == 0 or w == 0:
        return False

    aspect_ratio = w / h

    # ---- 1. 宽高比 ----
    # 机动车灯：合并成组后通常横向宽，但单个灯盘检测也可能偏窄
    # 行人灯：纵向高窄（人形图标 + 数字倒计时），w/h 通常 < 0.35
    if aspect_ratio < min_aspect_ratio:
        logger.debug(
            f"[机动车/行人灯] 宽高比={aspect_ratio:.2f} < {min_aspect_ratio} → 疑似行人灯"
        )
        return False

    # ---- 2. 亮斑数量（通过 HSV 亮度通道 + 轮廓分析） ----
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]  # 亮度通道，红灯也能正确反映

    # 自适应亮度阈值：取均值以上区域作为高亮候选
    bright_thresh = max(120, int(np.mean(v_channel) + 25))
    _, bright_mask = cv2.threshold(v_channel, bright_thresh, 255, cv2.THRESH_BINARY)

    # 形态学去噪
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(
        bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # 筛选出面积足够大且近似圆形的亮斑
    min_area = (w * h) * 0.002  # 至少 0.2% 面积
    max_area = (w * h) * 0.25  # 不超过 25%
    bright_spot_count = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        # 圆度 = 4π × 面积 / 周长² → 1.0 = 完美圆
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter**2)
        # 机动车灯盘 ≈ 圆形，允许一定椭圆度 (0.35~1.0)
        if 0.35 < circularity <= 1.0:
            bright_spot_count += 1

    if bright_spot_count < min_bright_spots:
        logger.debug(
            f"[机动车/行人灯] 圆形亮斑数={bright_spot_count} < {min_bright_spots} → 疑似行人灯"
        )
        return False

    # ---- 3. 彩色像素占比（辅助判断） ----
    # 复用上面已计算的 hsv
    lower_red1 = np.array([0, 30, 40])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 30, 40])
    upper_red2 = np.array([180, 255, 255])
    lower_yellow = np.array([20, 30, 40])
    upper_yellow = np.array([35, 255, 255])
    lower_green = np.array([36, 30, 40])
    upper_green = np.array([85, 255, 255])

    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(
        hsv, lower_red2, upper_red2
    )
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    colored_mask = mask_red | mask_yellow | mask_green

    total_pixels = colored_mask.size
    colored_ratio = np.count_nonzero(colored_mask) / total_pixels
    red_ratio = np.count_nonzero(mask_red) / total_pixels
    green_ratio = np.count_nonzero(mask_green) / total_pixels

    # 机动车灯：红绿黄三色分布较均匀
    # 行人灯：通常只有红或绿一种颜色明显（人形图标为单色）
    has_red = red_ratio > 0.002
    has_green = green_ratio > 0.002
    if colored_ratio < min_colored_ratio:
        logger.debug(
            f"[机动车/行人灯] 彩色占比={colored_ratio:.4f} < {min_colored_ratio} → 疑似行人灯"
        )
        return False

    logger.debug(
        f"[机动车/行人灯] VEHICLE "
        f"宽高比={aspect_ratio:.2f} 亮斑={bright_spot_count} "
        f"彩色={colored_ratio:.4f} 红={has_red} 绿={has_green}"
    )

    return True


def classify_traffic_light(
    crop: np.ndarray,
) -> str:
    """综合分类：正面机动车灯 / 行人交通灯 / 背面。

    Args:
        crop: 裁剪后的红绿灯图像（BGR 格式）。

    Returns:
        "vehicle" | "pedestrian" | "back"
    """
    if not is_front_facing(crop):
        return "back"
    if not is_vehicle_traffic_light(crop):
        return "pedestrian"
    return "vehicle"
