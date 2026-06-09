"""画框标注 — 在图片上绘制检测框和类别标签。"""

from PIL import Image, ImageDraw, ImageFont

from detector.models.detect_model import Detection

# ── 检测框颜色（按类别区分） ──
COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "off": (128, 128, 128),
    "wait_on": (255, 165, 0),
}

# ── 标签字体 ──
try:
    FONT = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=24
    )
except OSError:
    FONT = ImageFont.load_default()


def draw_detections(
    img: Image.Image,
    detections: list[Detection],
    *,
    expand_ratio: float = 0.15,
) -> Image.Image:
    """在图片上绘制检测框和类别标签，返回标注后的副本。

    Args:
        img: 原始 PIL 图片。
        detections: 检测结果列表。
        expand_ratio: 框向外扩展的比例（默认 0.15 即 15%）。
    """
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)

    for det in detections:
        cls_name = det.class_name
        x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)

        # 向外扩展框
        bw, bh = x2 - x1, y2 - y1
        pad_w, pad_h = int(bw * expand_ratio), int(bh * expand_ratio)
        x1, y1 = x1 - pad_w, y1 - pad_h
        x2, y2 = x2 + pad_w, y2 + pad_h

        color = COLORS.get(cls_name, (255, 255, 255))

        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        # 标签放在检测框下方
        text = cls_name
        text_x, text_y = x1, y2 + 2
        bbox = draw.textbbox((text_x + 4, text_y + 2), text, font=FONT)
        pad = 4
        draw.rectangle([text_x, text_y, bbox[2] + pad, bbox[3] + pad], fill=color)
        draw.text((text_x + 4, text_y + 2), text, fill=(255, 255, 255), font=FONT)

    return annotated
