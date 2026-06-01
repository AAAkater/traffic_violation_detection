"""红绿灯检测入口 — 直接运行即可执行完整检测流水线。"""

from detector.pipeline import run_batch

if __name__ == "__main__":
    run_batch(
        dataset_dir="",
        model_path="",
        conf_threshold=0.5,
    )
