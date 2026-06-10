"""空间过滤器 — 根据检测框在图像中的位置过滤非目标区域。"""

from detector.models.detect_model import Detection
from detector.utils import logger


def filter_spatial(
    detections: list[Detection],
    image_height: int,
    image_width: int,
    *,
    upper_ratio: float = 0.5,
    edge_ratio: float = 0.20,
    label: str = "",
) -> list[Detection]:
    """按空间位置过滤检测框：仅保留上半中间区域。

    Args:
        detections: 原始检测结果列表。
        image_height: 图片高度（像素）。
        image_width: 图片宽度（像素）。
        upper_ratio: 上半区域比例，低于该 y 坐标的检测框保留。
        edge_ratio: 两侧边缘比例，左右各剔除该比例的框。
        label: 日志前缀标签。

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
        logger.debug(f"{prefix}剔除 {removed_lower} 个下半区域框, 保留 {len(kept)} 个")
    if removed_edge:
        logger.debug(f"{prefix}剔除 {removed_edge} 个边缘框, 保留 {len(kept)} 个")

    return kept
