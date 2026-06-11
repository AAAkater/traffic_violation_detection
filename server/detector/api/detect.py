"""检测端点 — 上传图片，返回红绿灯检测框坐标和类别名称，结果持久化到数据库。"""

import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from detector.common.response import DetectData, DetectionItem, Response
from detector.db import DetectImage, DetectionBox, get_db, upload_bytes
from detector.detect import detect_pipeline
from detector.settings import settings
from detector.utils import logger
from detector.utils.image_tools import preprocess_single

router = APIRouter()


@router.post("/detect")
async def detect(
    image_file: UploadFile = File(..., alias="image_file"),
    db: AsyncSession = Depends(get_db),
):
    """上传原始图片，执行 YOLO 检测，返回所有检测框的坐标和类别名称，并保存到数据库。"""
    contents = await image_file.read()

    try:
        logger.debug("[detect] ========== 开始检测请求 ==========")
        logger.debug(
            f"[detect] 文件名: {image_file.filename}, 大小: {len(contents)} bytes"
        )

        # ── 0. 生成图片唯一标识 & 上传原始图片到 RustFS ──
        image_id = uuid.uuid4().hex[:16]
        image_url = upload_bytes(
            data=contents,
            filename=image_file.filename,
            prefix="detect",
        )
        logger.info(f"[detect] 原始图片已上传: {image_url}")

        # ── 1. 预处理：裁剪象限 ──
        img = Image.open(io.BytesIO(contents))
        quadrants = preprocess_single(img)
        logger.debug(f"[detect] 裁剪出 {len(quadrants)} 个象限")

        # ── 2. YOLO 检测 ──
        detect_quadrants = {
            k: v
            for k, v in quadrants.items()
            if k in ("top_left", "top_right", "bottom_left")
        }
        _, raw_detections = detect_pipeline(
            quadrant_images=detect_quadrants,
            model_path=settings.yolo_model_path,
            conf_threshold=settings.yolo_conf_threshold,
            device=settings.yolo_device,
        )

        # ── 3. 汇总检测结果 ──
        items: list[DetectionItem] = []
        for quadrant_name, dets in raw_detections.items():
            for d in dets:
                items.append(
                    DetectionItem(
                        quadrant=quadrant_name,
                        bbox=d.bbox,
                        confidence=d.confidence,
                        class_name=d.class_name,
                    )
                )

        # ── 4. 保存检测结果到数据库 ──
        filename = image_file.filename or "upload"
        db.add(
            DetectImage(
                image_id=image_id,
                filename=filename,
                image_url=image_url,
            )
        )
        for item in items:
            record = DetectionBox(
                image_id=image_id,
                quadrant=item.quadrant,
                bbox=item.bbox,
                confidence=item.confidence,
                class_name=item.class_name,
            )
            db.add(record)

        logger.debug(f"[detect] 检测完成, 共 {len(items)} 个检测框")
        logger.debug("[detect] ========== 检测请求完成 ==========")

        return Response(
            data=DetectData(
                image_id=image_id,
                detections=items,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[detect] 检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
