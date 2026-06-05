"""YOLO inference script for traffic light detection.

Input: 指向 红绿灯违章_cropped/ 这样的文件夹，结构如下：
    红绿灯违章_cropped/
    ├── 710710/
    │   ├── 710710.jpg          ← 原图（不参与推理）
    │   └── cropped/
    │       ├── topleft.jpg
    │       ├── topright.jpg
    │       └── bottomleft.jpg
    ├── 1005977/
    │   └── ...

Output: 推理结果保存到每个子文件夹的 tags/ 目录：
    710710/
    ├── cropped/
    │   ├── topleft.jpg
    │   ├── topright.jpg
    │   └── bottomleft.jpg
    └── tags/
        ├── topleft_det.jpg
        ├── topright_det.jpg
        └── bottomleft_det.jpg

Usage:
    python yolo_infernce.py /path/to/红绿灯违章_cropped
    python yolo_infernce.py /path/to/红绿灯违章_cropped --conf 0.6
    python yolo_infernce.py /path/to/红绿灯违章_cropped/710710/cropped   # 单个子文件夹
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_PATH = (
    "/home/AAAkater/workspace/python/models/Ultralytics/YOLO26_sft/best.pt"
)
IMGSZ = 1280
DEFAULT_CONF = 0.5

COLORS = {
    "red": (255, 0, 0),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "off": (128, 128, 128),
    "wait_on": (255, 165, 0),
}

# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def _load_font(size: int = 36) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font, fall back to default."""
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def draw_detections(
    img: Image.Image,
    results,
    model: YOLO,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None,
) -> Image.Image:
    """Draw bounding boxes with class labels on *img* (in-place) and return it."""
    if font is None:
        font = _load_font()

    draw = ImageDraw.Draw(img)

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            color = COLORS.get(cls_name, (255, 255, 255))

            # Bounding box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=4)

            # Label background + text (class name only, no confidence)
            text = cls_name
            bbox = draw.textbbox((x1, y1), text, font=font)
            text_h = bbox[3] - bbox[1]
            draw.rectangle([x1, y1 - text_h - 8, bbox[2] + 8, y1], fill=color)
            draw.text(
                (x1 + 4, y1 - text_h - 8), text, fill=(255, 255, 255), font=font
            )

    return img


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------


def infer_single(model: YOLO, img_path: Path, conf: float) -> Image.Image:
    """Run inference on a single image and return the annotated image."""
    results = model.predict(
        source=str(img_path), imgsz=IMGSZ, conf=conf, verbose=False
    )
    img = Image.open(img_path).convert("RGB")
    draw_detections(img, results, model)
    return img


def process_cropped_dir(model: YOLO, cropped_dir: Path, conf: float) -> None:
    """Process all images in a cropped/ directory, save results to ../tags/."""
    tags_dir = cropped_dir.parent / "tags"
    tags_dir.mkdir(exist_ok=True)

    img_files = sorted(
        f
        for f in cropped_dir.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        and not f.name.endswith("_det.jpg")
    )

    if not img_files:
        print(f"  No images found in {cropped_dir}, skipping.")
        return

    for img_file in img_files:
        print(f"  Processing {img_file.name} ...")
        img = infer_single(model, img_file, conf)
        out_path = tags_dir / f"{img_file.stem}_det.jpg"
        img.save(str(out_path), quality=95)
        print(f"    -> {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="YOLO traffic light inference")
    parser.add_argument("source", help="根目录或 cropped 子目录路径")
    parser.add_argument("--model", default=MODEL_PATH, help="模型权重路径")
    parser.add_argument(
        "--conf", type=float, default=DEFAULT_CONF, help="置信度阈值"
    )
    args = parser.parse_args()

    model = YOLO(args.model)
    source = Path(args.source)

    # Case 1: source is a cropped/ directory directly
    if source.name == "cropped" and source.is_dir():
        print(f"Processing single cropped directory: {source}")
        process_cropped_dir(model, source, args.conf)
        return

    # Case 2: source is a root directory containing sub-folders
    # e.g. 红绿灯违章_cropped/710710/cropped/
    sub_dirs = sorted(d for d in source.iterdir() if d.is_dir())
    cropped_dirs = [d / "cropped" for d in sub_dirs if (d / "cropped").is_dir()]

    if not cropped_dirs:
        # Fallback: treat source as a flat image directory
        print(
            f"No cropped/ sub-directories found, treating {source} as flat directory"
        )
        process_cropped_dir(model, source, args.conf)
        return

    print(f"Found {len(cropped_dirs)} cropped directories under {source}")
    for cropped_dir in cropped_dirs:
        print(f"\n[{cropped_dir.parent.name}]")
        process_cropped_dir(model, cropped_dir, args.conf)

    print(f"\nAll done! Processed {len(cropped_dirs)} directories.")


if __name__ == "__main__":
    main()
