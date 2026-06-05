"""预处理脚本 — 将纯图片文件夹裁剪为检测流水线所需的目录结构。

使用方式：
    1. 修改下方配置
    2. python preprocess.py
"""

from __future__ import annotations

from pathlib import Path

from detector.preprocess import preprocess

# ── 配置（直接修改此处即可）──────────────────────────────────
src_dir = ""
output_dir = ""
dry_run = False


if __name__ == "__main__":
    src = Path(src_dir)
    if not src.is_dir():
        raise SystemExit(f"源目录不存在: {src}")

    preprocess(src, Path(output_dir), dry_run=dry_run)
