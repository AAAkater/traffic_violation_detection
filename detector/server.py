"""FastAPI 服务 — 接收原始图片上传，执行完整检测+判定流水线并返回结果。

启动方式：
    uv run uvicorn detector.server:app --host 0.0.0.0 --port 8000

接口：
    POST /judge  — 上传一张原始图片，返回违法判定结果
    GET  /health — 健康检查
"""

from __future__ import annotations

import io
import shutil
import tempfile
from pathlib import Path

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
async def judge(file: UploadFile = File(...)):
    # 读取上传的图片
    contents = await file.read()
    stem = Path(file.filename or "upload").stem

    # 写入临时目录
    tmp_root = Path(tempfile.mkdtemp(prefix="tvd_"))
    try:
        # ── 1. 保存原图并预处理 ──
        img = Image.open(io.BytesIO(contents))
        sample_dir = tmp_root / stem
        preprocess_single(img, sample_dir)

        # ── 2. YOLO 检测 ──
        detect_run(
            sample_dir=str(sample_dir),
            model_path=settings.model_path,
            conf_threshold=settings.conf_threshold,
        )

        # ── 3. 加载图片直接传给 LLM ──
        root = sample_dir
        annotated_images: list[Image.Image] = []
        for eng in ("topleft", "topright", "bottomleft"):
            det_path = root / "tags" / f"{eng}_det.jpg"
            if not det_path.exists():
                raise HTTPException(status_code=400, detail=f"缺少标注图: {det_path}")
            annotated_images.append(Image.open(det_path))

        suspect_path = root / "tags" / "bottomright.jpg"
        if not suspect_path.exists():
            raise HTTPException(status_code=400, detail="缺少嫌疑车辆图")
        suspect_image = Image.open(suspect_path)

        client = VisionClient(
            model=settings.judge_model,
            base_url=settings.judge_base_url,
            api_key=settings.judge_api_key,
            max_tokens=settings.judge_max_tokens,
            temperature=settings.judge_temperature,
        )
        result = await client.judge_violation(
            annotated_images=annotated_images,
            suspect_image=suspect_image,
        )

        return Response(
            code=0,
            msg="success",
            data=JudgeData(
                sample_id=stem,
                violated=result.violated,
                reason=result.reason,
            ),
        )

    except Exception as e:
        logger.error(f"[server] 判定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 清理临时目录
        shutil.rmtree(tmp_root, ignore_errors=True)
