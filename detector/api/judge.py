"""违法判定端点。"""

import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image

from detector.common.response import JudgeData, Response
from detector.detect import run as detect_run
from detector.models import TrafficLightDetector
from detector.models.judge_model import VisionClient
from detector.settings import settings
from detector.utils import logger
from detector.utils.image_tools import (
    compress_to_1080p,
    preprocess_single,
    redraw_detections_on_compressed,
    save_debug_images,
)

router = APIRouter()


@router.post("/judge")
async def judge(image_file: UploadFile = File(..., alias="image_file")):
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

        # ── 2. YOLO 检测（用原始分辨率，保证检测精度）──
        logger.debug(
            "[server] 阶段2: YOLO 检测 — 在原始分辨率上对 top_left/top_right/bottom_left 进行检测..."
        )
        detect_quadrants = {
            k: v
            for k, v in quadrants.items()
            if k in ("top_left", "top_right", "bottom_left")
        }
        annotated_images, raw_detections = detect_run(
            quadrant_images=detect_quadrants,
            model_path=settings.yolo_model_path,
            conf_threshold=settings.yolo_conf_threshold,
            device=settings.yolo_device,
        )
        logger.debug(
            f"[server] 阶段2完成: 检测完成, 标注图 keys={list(annotated_images.keys())}"
        )

        # ── 3. 压缩象限到 1080P，用原始检测坐标重新画框 ──
        logger.debug("[server] 阶段3: 压缩象限到1080P并重绘检测框...")
        compressed_detect = {
            k: compress_to_1080p(v) for k, v in detect_quadrants.items()
        }
        suspect_compressed = compress_to_1080p(quadrants["bottom_right"])

        redraw_detector = TrafficLightDetector(
            settings.yolo_model_path,
            device=settings.yolo_device,
            conf_threshold=settings.yolo_conf_threshold,
        )
        annotated_1080p = redraw_detections_on_compressed(
            original_images=detect_quadrants,
            compressed_images=compressed_detect,
            detections=raw_detections,
            detector=redraw_detector,
        )
        logger.debug("[server] 阶段3完成: 重绘完成")

        # ── 4. 保存本地、传给 LLM ──
        logger.debug("[server] 阶段4: 保存图片并调用 LLM 判定...")
        ordered_keys = ["top_left_det", "top_right_det", "bottom_left_det"]
        for key in ordered_keys:
            if key not in annotated_1080p:
                raise HTTPException(status_code=400, detail=f"缺少标注图: {key}")

        saved_dir = save_debug_images(annotated_1080p, suspect_compressed)
        logger.info(f"[server] 阶段4: 图片已保存至 {saved_dir}")

        annotated_list = [annotated_1080p[k] for k in ordered_keys]
        logger.debug("[server] 阶段4准备就绪: 3张标注图 + 1张嫌疑图")

        client = VisionClient(
            model=settings.judge_model,
            base_url=settings.judge_base_url,
            api_key=settings.judge_api_key,
        )
        result = await client.judge_violation(
            annotated_images=annotated_list,
            suspect_image=suspect_compressed,
        )
        logger.debug(
            f"[server] 阶段4完成: violated={result.violated}, reason={result.reason}"
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
