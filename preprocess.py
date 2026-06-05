"""预处理脚本：将纯图片文件夹裁剪为检测流水线所需的目录结构。

输入：一个包含纯图片的文件夹，如 assets/
    assets/
    ├── 710710.jpg
    ├── 1013006.jpg
    └── ...

输出：裁剪后的目录结构，供 yolo_infernce.py 或 pipeline 使用：
    output/
    ├── 710710/
    │   ├── 710710.jpg          ← 原图副本
    │   ├── cropped/
    │   │   ├── topleft.jpg
    │   │   ├── topright.jpg
    │   │   └── bottomleft.jpg
    │   └── tags/
    │       └── bottomright.jpg  ← 右下角（不参与检测，仅保留）
    ├── 1013006/
    │   ├── 1013006.jpg
    │   ├── cropped/
    │   │   └── ...
    │   └── tags/
    │       └── bottomright.jpg
    └── ...

裁剪方式：以 (width//2, height//2) 为中点，
  - 左上: (0, 0) -> (mid_x, mid_y)        → cropped/
  - 右上: (mid_x, 0) -> (width, mid_y)     → cropped/
  - 左下: (0, mid_y) -> (mid_x, height)     → cropped/
  - 右下: (mid_x, mid_y) -> (width, height) → tags/

Usage:
    python preprocess.py assets/ -o output/
    python preprocess.py assets/ -o output/ --dry-run   # 只打印，不写文件
"""

import argparse
import shutil
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

REGIONS = {
    "topleft": lambda w, h: (0, 0, w // 2, h // 2),
    "topright": lambda w, h: (w // 2, 0, w, h // 2),
    "bottomleft": lambda w, h: (0, h // 2, w // 2, h),
}


def BOTTOMRIGHT(w, h):
    return (w // 2, h // 2, w, h)


def preprocess(src_dir: Path, dst_dir: Path, *, dry_run: bool = False) -> None:
    """将 src_dir 中的所有图片裁剪并组织到 dst_dir 中。

    每张图片生成一个子文件夹，包含原图副本、cropped/ 子目录（3 个裁剪块）
    和 tags/ 子目录（右下角裁剪块）。
    """
    image_files = sorted(f for f in src_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS)
    if not image_files:
        print(f"未在 {src_dir} 中找到图片文件")
        return

    print(f"找到 {len(image_files)} 张图片")

    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)

    for img_path in image_files:
        img = Image.open(img_path)
        w, h = img.size
        stem = img_path.stem
        suffix = img_path.suffix

        sub_dir = dst_dir / stem
        cropped_dir = sub_dir / "cropped"
        tags_dir = sub_dir / "tags"

        if dry_run:
            print(f"  {img_path.name} ({w}x{h}) -> {sub_dir}/")
            print(f"    原图 -> {sub_dir / img_path.name}")
            for name, box_fn in REGIONS.items():
                box = box_fn(w, h)
                print(f"    {name} -> {cropped_dir / f'{name}{suffix}'}  {box}")
            print(
                f"    bottomright -> {tags_dir / f'bottomright{suffix}'}  {BOTTOMRIGHT(w, h)}"
            )
            continue

        sub_dir.mkdir(exist_ok=True)
        cropped_dir.mkdir(exist_ok=True)
        tags_dir.mkdir(exist_ok=True)

        # 复制原图
        shutil.copy2(img_path, sub_dir / img_path.name)

        # 裁剪并保存到 cropped/
        for name, box_fn in REGIONS.items():
            box = box_fn(w, h)
            cropped = img.crop(box)
            cropped.save(cropped_dir / f"{name}{suffix}")

        # 右下角保存到 tags/
        br_box = BOTTOMRIGHT(w, h)
        img.crop(br_box).save(tags_dir / f"bottomright{suffix}")

        print(f"  {img_path.name} ({w}x{h}) -> 3 crops + bottomright saved")

    print(f"\n完成！{'(dry-run)' if dry_run else ''} 输出目录: {dst_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="预处理：将纯图片文件夹裁剪为检测流水线所需的目录结构"
    )
    parser.add_argument(
        "src_dir",
        help="源图片文件夹路径（如 assets/）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出文件夹路径（默认: <src_dir>_cropped）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印操作，不实际写文件",
    )
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    if not src_dir.is_dir():
        raise SystemExit(f"源目录不存在: {src_dir}")

    dst_dir = (
        Path(args.output) if args.output else src_dir.parent / f"{src_dir.name}_cropped"
    )
    preprocess(src_dir, dst_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
