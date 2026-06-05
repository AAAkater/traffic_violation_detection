"""红绿灯检测脚本 — 对预处理后的图片执行 YOLO 检测、空间过滤、画框保存。

使用方式：
    1. 先运行预处理：python preprocess.py assets/ -o output/
    2. 再运行检测：  python detect.py
    3. 最后运行判定：python judge.py

本脚本等价于 detector.pipeline.run_batch，可独立运行。
"""

from detector.detect import run_batch

# ── 配置（直接修改此处即可）──────────────────────────────────
preprocessed_dir = ""
model_path = ""
conf_threshold = 0.4
# ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    run_batch(
        preprocessed_dir=preprocessed_dir,
        model_path=model_path,
        conf_threshold=conf_threshold,
    )
