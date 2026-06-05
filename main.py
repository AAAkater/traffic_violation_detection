"""红绿灯检测 + 违法判定整合流水线入口。

使用方式：
    1. 先运行预处理：python preprocess.py assets/ -o output/
    2. 再运行检测+判定：python main.py

检测模块作为生产者（快），产出裁剪后的交通灯图片；
判定模块作为消费者（慢），以指定并发数消费检测产出的任务。
"""

from detector.integrated_pipeline import run_pipeline
from detector.settings import PipelineSettings

if __name__ == "__main__":
    settings = PipelineSettings()  # type: ignore[call-arg]
    run_pipeline(
        preprocessed_dir=settings.preprocessed_dir,
        model_path=settings.detection.model_path,
        conf_threshold=settings.detection.conf_threshold,
        # 判定模块参数
        judge=settings.judge.enabled,
        judge_model="qwen3.7-plus",
        judge_base_url=settings.judge.base_url,
        judge_api_key="",
        judge_concurrency=10,
    )
