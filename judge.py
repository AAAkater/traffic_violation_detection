"""违法判定脚本 — 对检测完成的样本执行多模态模型判定。

使用方式：
    1. 先运行预处理：python preprocess.py assets/ -o output/
    2. 再运行检测：  python detect.py
    3. 最后运行判定：python judge.py
"""

from __future__ import annotations

import asyncio

from detector.judge import run_judge

# ── 配置 ──────────────────────────────────────────────────────
preprocessed_dir = ""
model = "qwen3.7-plus"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key = ""
concurrency = 10
max_tokens = 20000
temperature = 0.0


if __name__ == "__main__":
    asyncio.run(
        run_judge(
            preprocessed_dir=preprocessed_dir,
            model=model,
            base_url=base_url,
            api_key=api_key,
            concurrency=concurrency,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
