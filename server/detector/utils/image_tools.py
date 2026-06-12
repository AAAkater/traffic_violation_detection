"""图片工具 — 单图预处理（象限裁剪）等图像处理辅助函数。"""

from pathlib import Path

from PIL import Image

from detector.models.detect import Detection

from .draw import draw_detections

_TARGET_1080P = 1080
"""1080P 压缩目标：长边不超过此像素数。"""


def compress_to_1080p(img: Image.Image) -> Image.Image:
    """将图片压缩到长边不超过 1080 像素（保持宽高比）。

    若原图长边已 ≤ 1080 则不缩放。
    """
    w, h = img.size
    max_edge = max(w, h)
    if max_edge <= _TARGET_1080P:
        return img.copy()

    scale = _TARGET_1080P / max_edge
    new_size = (int(w * scale), int(h * scale))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def redraw_detections_on_compressed(
    original_images: dict[str, Image.Image],
    compressed_images: dict[str, Image.Image],
    detections: dict[str, list],  # list[Detection]
) -> dict[str, Image.Image]:
    """将原始分辨率的检测框坐标映射到压缩图上重新绘制。

    先用原始分辨率图片跑 YOLO 检测获得准确的 bbox 坐标，
    再将坐标按缩放比例映射到压缩后的图片上画框，
    保证检测精度的同时框线不会因压缩而变形。

    Args:
        original_images: 原始分辨率象限图，key 为 eng_name。
        compressed_images: 压缩后的象限图，key 为 eng_name。
        detections: 原始检测结果，key 为 eng_name，value 为 Detection 列表。

    Returns:
        在压缩图上绘制了检测框的新图片，key 为 "{eng_name}_det"。
    """
    annotated: dict[str, Image.Image] = {}

    for eng_name, comp_img in compressed_images.items():
        orig_img = original_images.get(eng_name)
        dets = detections.get(eng_name, [])

        if not dets or orig_img is None:
            annotated[f"{eng_name}_det"] = comp_img
            continue

        # 计算缩放比例
        ow, oh = orig_img.size
        cw, ch = comp_img.size
        sx, sy = cw / ow, ch / oh

        # 将 Detection 坐标映射到压缩图
        scaled: list[Detection] = []
        for d in dets:
            scaled.append(
                Detection(
                    bbox=[
                        d.x1 * sx,
                        d.y1 * sy,
                        d.x2 * sx,
                        d.y2 * sy,
                    ],
                    confidence=d.confidence,
                    class_name=d.class_name,
                )
            )

        annotated[f"{eng_name}_det"] = draw_detections(comp_img, scaled)

    return annotated


def save_debug_images(
    annotated_images: dict[str, Image.Image],
    suspect_image: Image.Image,
    output_dir: str | Path = "output/judge_inputs",
) -> Path:
    """将标注图和嫌疑图保存到本地目录，方便人工检查。

    Args:
        annotated_images: {"top_left_det": Image, ...} 标注图字典。
        suspect_image: 嫌疑车辆图（右下象限）。
        output_dir: 输出目录路径。

    Returns:
        实际保存的目录 Path。
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for key, img in annotated_images.items():
        img.save(out / f"{key}.jpg", format="JPEG", quality=95)

    suspect_image.save(out / "suspect.jpg", format="JPEG", quality=95)
    return out


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
