"""FastAPI 服务 — 接收原始图片上传，执行完整检测+判定流水线并返回结果。

启动方式：
    uv run uvicorn detector.server:app --host 0.0.0.0 --port 8000

接口：
    POST /judge  — 上传一张原始图片，返回违法判定结果
    GET  /health — 健康检查
"""

import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

from detector.common.response import JudgeData, Response
from detector.detect import run as detect_run
from detector.models.judge_model import VisionClient
from detector.settings import settings
from detector.utils import logger
from detector.utils.image_tools import preprocess_single

app = FastAPI(title="交通违法判定服务", version="0.1.0")


@app.post("/judge")
async def judge(image_file: UploadFile = File(..., alias="file")):
    # 读取上传的图片
    contents = await image_file.read()

    try:
        logger.debug("[server] ========== 开始处理请求 ==========")
        logger.debug(
            f"[server] 文件名: {image_file.filename}, 大小: {len(contents)} bytes"
        )

        # ── 1. 预处理：裁剪象限（纯内存） ──
        logger.debug("[server] 阶段1: 图片预处理 — 打开图像并裁剪象限...")
        img = Image.open(io.BytesIO(contents))
        quadrants = preprocess_single(img)
        logger.debug(f"[server] 阶段1完成: 裁剪出 {len(quadrants)} 个象限")

        # ── 2. YOLO 检测（纯内存） ──
        logger.debug(
            "[server] 阶段2: YOLO 检测 — 对 top_left / top_right / bottom_left 进行目标检测..."
        )
        detect_quadrants = {
            k: v
            for k, v in quadrants.items()
            if k in ("top_left", "top_right", "bottom_left")
        }
        annotated_images = detect_run(
            quadrant_images=detect_quadrants,
            model_path=settings.yolo_model_path,
            conf_threshold=settings.yolo_conf_threshold,
            device=settings.yolo_device,
        )
        logger.debug(
            f"[server] 阶段2完成: 检测完成, 标注图 keys={list(annotated_images.keys())}"
        )

        # ── 3. 组装图片传给 LLM ──
        logger.debug("[server] 阶段3: 组装标注图并调用 LLM 判定...")
        ordered_keys = ["top_left_det", "top_right_det", "bottom_left_det"]
        annotated_list: list[Image.Image] = []
        for key in ordered_keys:
            if key not in annotated_images:
                raise HTTPException(status_code=400, detail=f"缺少标注图: {key}")
            annotated_list.append(annotated_images[key])

        suspect_image = quadrants["bottom_right"]
        logger.debug("[server] 阶段3准备就绪: 3张标注图 + 1张嫌疑图")

        client = VisionClient(
            model=settings.judge_model,
            base_url=settings.judge_base_url,
            api_key=settings.judge_api_key,
        )
        result = await client.judge_violation(
            annotated_images=annotated_list,
            suspect_image=suspect_image,
        )
        logger.debug(
            f"[server] 阶段3完成: violated={result.violated}, reason={result.reason}"
        )

        logger.debug("[server] ========== 请求处理完成 ==========")
        return Response(
            data=JudgeData(
                filename=image_file.filename or "upload",
                violated=result.violated,
                reason=result.reason,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[server] 判定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
