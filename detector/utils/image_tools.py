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


def crop_upper_region(
    image: np.ndarray,
    upper_ratio: float = 0.5,
    edge_ratio: float = 0.20,
) -> tuple[np.ndarray, int, int]:
    """裁剪图片的上半区域（可同时去掉左右边缘），返回裁剪图和偏移量。

    在行车记录仪画面中，红绿灯通常位于画面上方且不在水平边缘。
    先裁剪再送入 YOLO 检测，可以减少检测范围、提高速度和准确性。

    Args:
        image: 原始图像（BGR 格式 numpy 数组）。
        upper_ratio: 保留上半区域的比例，默认 0.5 即上半 50%。
        edge_ratio: 左右边缘剔除比例，默认 0.20 即去掉左右各 20%。
            设为 0 则保留完整水平宽度。

    Returns:
        (cropped, offset_y, offset_x): 裁剪后的图像 + Y 方向偏移 + X 方向偏移。
        检测结果的坐标加上偏移即可映射回原图坐标。
    """
    h, w = image.shape[:2]
    cutoff_y = int(h * upper_ratio)
    cutoff_x_left = int(w * edge_ratio)
    cutoff_x_right = int(w * (1 - edge_ratio))

    cropped = image[0:cutoff_y, cutoff_x_left:cutoff_x_right]
    return cropped, 0, cutoff_x_left


def save_cropped_region(
    image: np.ndarray,
    output_path: str,
) -> str:
    """保存裁剪后的区域图片到文件。

    Args:
        image: 裁剪后的图像（BGR 格式 numpy 数组）。
        output_path: 输出文件路径。

    Returns:
        保存的文件路径。
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)
    logger.debug(f"已保存裁剪区域图: {path}")
    return str(path)


def compress_image_to_1080p(
    src: str | Path,
    dst: str | Path | None = None,
    *,
    max_w: int = 1920,
    max_h: int = 1080,
    quality: int = 90,
) -> str | None:
    """将单张图片压缩到指定分辨率（默认 1080p）。

    Args:
        src: 源图片路径。
        dst: 目标保存路径。为 None 时原地覆盖保存，保持文件名不变。
        max_w: 最大宽度，默认 1920。
        max_h: 最大高度，默认 1080。
        quality: JPEG 保存质量，默认 90。

    Returns:
        保存的文件路径；读取失败时返回 None。
    """
    src = Path(src)
    if not src.exists():
        return None
    img = cv2.imread(str(src))
    if img is None:
        return None
    h, w = img.shape[:2]
    if w > max_w or h > max_h:
        scale = min(max_w / w, max_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug(f"已压缩 {src.name}: {w}×{h} → {new_w}×{new_h}")
    save_path = str(dst) if dst is not None else str(src)
    cv2.imwrite(save_path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return save_path


def compress_images_to_1080p(
    image_dir: str,
    *,
    max_w: int = 1920,
    max_h: int = 1080,
    quality: int = 90,
) -> list[str]:
    """将目录下的所有图片压缩到指定分辨率（默认 1080p），原地覆盖保存。

    Args:
        image_dir: 图片目录路径。
        max_w: 最大宽度，默认 1920。
        max_h: 最大高度，默认 1080。
        quality: JPEG 保存质量，默认 90。

    Returns:
        压缩后的文件路径列表。
    """
    dir_path = Path(image_dir)
    if not dir_path.exists():
        return []

    saved: list[str] = []
    for img_file in sorted(dir_path.glob("*.*")):
        if img_file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            continue
        result = compress_image_to_1080p(
            img_file, max_w=max_w, max_h=max_h, quality=quality
        )
        if result is not None:
            saved.append(result)
    return saved


def compress_quadrants_to_1080p(quadrants_dir: str) -> list[str]:
    """将象限图目录下的所有图片压缩到 1080p（长边 ≤ 1920，短边 ≤ 1080）。

    原地覆盖保存，保持文件名不变。
    等价于 ``compress_images_to_1080p(quadrants_dir)``。

    Args:
        quadrants_dir: 象限图目录路径。

    Returns:
        压缩后的文件路径列表。
    """
    return compress_images_to_1080p(quadrants_dir)


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
