"""FastAPI 服务入口 — 接收原始图片上传，执行完整检测+判定流水线并返回结果。

启动方式：
    uv run uvicorn main:app --host 0.0.0.0 --port 8000

    或直接运行：
    uv run python main.py

接口：
    POST /v1/judge  — 上传一张原始图片，返回违法判定结果
    GET  /v1/health — 健康检查
"""

from fastapi import FastAPI

from detector.api import lifespan, v1_router

app = FastAPI(title="交通违法判定服务", version="0.1.0", lifespan=lifespan)
app.include_router(v1_router)
