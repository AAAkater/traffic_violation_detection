"""图片工具 — 单图预处理（象限裁剪）等图像处理辅助函数。"""

from PIL import Image


def preprocess_single(img: Image.Image) -> dict[str, Image.Image]:
    """将单张原始图片按宽高中点裁剪为 4 个象限，返回象限名到裁剪图的映射。

    返回的象限名与用途：
        - top_left     ← 左上（检测象限）
        - top_right    ← 右上（检测象限）
        - bottom_left  ← 左下（检测象限）
        - bottom_right ← 右下（嫌疑车辆）

    Args:
        img: 原始 PIL Image。

    Returns:
        {"top_left": Image, "top_right": Image, "bottom_left": Image, "bottom_right": Image}
    """
    w, h = img.size
    mid_x, mid_y = w // 2, h // 2

    quadrants: dict[str, Image.Image] = {}
    for name, box in [
        ("top_left", (0, 0, mid_x, mid_y)),
        ("top_right", (mid_x, 0, w, mid_y)),
        ("bottom_left", (0, mid_y, mid_x, h)),
    ]:
        quadrants[name] = img.crop(box)

    quadrants["bottom_right"] = img.crop((mid_x, mid_y, w, h))
    return quadrants
