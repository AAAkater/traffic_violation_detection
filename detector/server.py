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
        # ── 1. 预处理：裁剪象限（纯内存） ──
        img = Image.open(io.BytesIO(contents))
        quadrants = preprocess_single(img)

        # ── 2. YOLO 检测（纯内存） ──
        detect_quadrants = {
            k: v
            for k, v in quadrants.items()
            if k in ("topleft", "topright", "bottomleft")
        }
        _stats, annotated_images = detect_run(
            quadrant_images=detect_quadrants,
            model_path=settings.yolo_model_path,
            conf_threshold=settings.yolo_conf_threshold,
            device=settings.yolo_device,
        )

        # ── 3. 组装图片传给 LLM ──
        ordered_keys = ["topleft_det", "topright_det", "bottomleft_det"]
        annotated_list: list[Image.Image] = []
        for key in ordered_keys:
            if key not in annotated_images:
                raise HTTPException(status_code=400, detail=f"缺少标注图: {key}")
            annotated_list.append(annotated_images[key])

        suspect_image = quadrants["bottomright"]

        client = VisionClient(
            model=settings.judge_model,
            base_url=settings.judge_base_url,
            api_key=settings.judge_api_key,
        )
        result = await client.judge_violation(
            annotated_images=annotated_list,
            suspect_image=suspect_image,
        )

        return Response(
            code=0,
            msg="success",
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
