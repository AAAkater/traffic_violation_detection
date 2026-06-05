"""预处理核心逻辑 — 将原始图片按象限裁剪并组织为检测所需的目录结构。"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

from detector.utils.image_tools import preprocess_single

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

REGIONS = {
    "topleft": lambda w, h: (0, 0, w // 2, h // 2),
    "topright": lambda w, h: (w // 2, 0, w, h // 2),
    "bottomleft": lambda w, h: (0, h // 2, w // 2, h),
}


def preprocess(src_dir: Path, dst_dir: Path, *, dry_run: bool = False) -> None:
    """将 src_dir 中的所有图片裁剪并组织到 dst_dir 中。

    每张图片生成一个子文件夹，包含原图副本、cropped/ 子目录（3 个裁剪块）
    和 tags/ 子目录（右下角裁剪块）。

        样本目录/
        ├── xxx.jpg           ← 原图副本
        ├── cropped/
        │   ├── topleft.jpg
        │   ├── topright.jpg
        │   └── bottomleft.jpg
        └── tags/
            └── bottomright.jpg

    Args:
        src_dir: 源图片文件夹。
        dst_dir: 输出根目录。
        dry_run: 仅打印操作，不写文件。
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

        if dry_run:
            print(f"  {img_path.name} ({w}x{h}) -> {sub_dir}/")
            print(f"    原图 -> {sub_dir / img_path.name}")
            for name, box_fn in REGIONS.items():
                box = box_fn(w, h)
                print(f"    {name} -> {sub_dir / 'cropped' / f'{name}{suffix}'}  {box}")
            br = (w // 2, h // 2, w, h)
            print(
                f"    bottomright -> {sub_dir / 'tags' / f'bottomright{suffix}'}  {br}"
            )
            continue

        # 复制原图
        sub_dir.mkdir(exist_ok=True)
        shutil.copy2(img_path, sub_dir / img_path.name)

        # 裁剪
        preprocess_single(img, sub_dir)

        print(f"  {img_path.name} ({w}x{h}) -> 3 crops + bottomright saved")

    print(f"\n完成！{'(dry-run)' if dry_run else ''} 输出目录: {dst_dir}")
