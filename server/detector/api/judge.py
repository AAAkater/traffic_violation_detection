"""违法判定端点 — 接收 image_id，从数据库获取原图和检测框，画框后传给 LLM 判定，结果持久化到数据库。"""

import io

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.api.prompt import get_system_prompt
from detector.common.response import JudgeData, Response
from detector.db import DetectImage, DetectionBox, JudgeRecord, get_db
from detector.db.storage import download_image
from detector.models.detect_model import Detection
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
async def judge(
    image_id: str,
    db: AsyncSession = Depends(get_db),
):
    """接收 image_id，从数据库获取原图和检测框，画框后传给 LLM 判定。

    Args:
        image_id: 检测接口返回的图片唯一标识。
        db: 数据库会话。
    """
    try:
        logger.debug("[judge] ========== 开始判定请求 ==========")
        logger.debug(f"[judge] image_id: {image_id}")

        # ── 0. 从数据库获取原图信息和检测框 ──
        img_result = await db.execute(
            select(DetectImage).where(DetectImage.image_id == image_id)
        )
        detect_image: DetectImage | None = img_result.scalar_one_or_none()
        if detect_image is None:
            raise HTTPException(status_code=404, detail=f"未找到图片: {image_id}")
        if not detect_image.image_url:
            raise HTTPException(
                status_code=400, detail=f"图片无 RustFS URL: {image_id}"
            )

        box_result = await db.execute(
            select(DetectionBox).where(DetectionBox.image_id == image_id)
        )
        detection_boxes: list[DetectionBox] = list(box_result.scalars().all())
        if not detection_boxes:
            raise HTTPException(status_code=400, detail=f"该图片无检测框: {image_id}")
        logger.debug(
            f"[judge] 从数据库获取: 原图={detect_image.image_url}, "
            f"检测框={len(detection_boxes)} 个"
        )

        # ── 1. 从 RustFS 下载原图 ──
        logger.debug("[judge] 阶段1: 从 RustFS 下载原图...")
        contents = download_image(detect_image.image_url)
        logger.debug(f"[judge] 阶段1完成: 下载 {len(contents)} bytes")

        # ── 2. 预处理：裁剪象限 ──
        logger.debug("[judge] 阶段2: 图片预处理 — 裁剪象限...")
        img = Image.open(io.BytesIO(contents))
        quadrants = preprocess_single(img)
        logger.debug(f"[judge] 阶段2完成: 裁剪出 {len(quadrants)} 个象限")

        # ── 3. 将检测框按象限分组 ──
        logger.debug("[judge] 阶段3: 将检测框按象限分组...")
        per_quadrant_detections: dict[str, list[Detection]] = {}
        for box in detection_boxes:
            d = Detection(
                bbox=box.bbox,
                confidence=box.confidence,
                class_name=box.class_name,
            )
            per_quadrant_detections.setdefault(box.quadrant, []).append(d)

        detect_quadrants = {
            k: v
            for k, v in quadrants.items()
            if k in ("top_left", "top_right", "bottom_left")
        }
        logger.debug(
            f"[judge] 阶段3完成: 检测象限={list(detect_quadrants.keys())}, "
            f"分组={list(per_quadrant_detections.keys())}"
        )

        # ── 4. 压缩到 1080P 并重绘检测框 ──
        logger.debug("[judge] 阶段4: 压缩象限到1080P并重绘检测框...")
        compressed_detect = {
            k: compress_to_1080p(v) for k, v in detect_quadrants.items()
        }
        suspect_compressed = compress_to_1080p(quadrants["bottom_right"])

        annotated_1080p = redraw_detections_on_compressed(
            original_images=detect_quadrants,
            compressed_images=compressed_detect,
            detections=per_quadrant_detections,
        )
        logger.debug("[judge] 阶段4完成: 压缩并重绘完成")

        # ── 5. 保存本地、传给 LLM ──
        logger.debug("[judge] 阶段5: 保存图片并调用 LLM 判定...")
        ordered_keys = ["top_left_det", "top_right_det", "bottom_left_det"]
        for key in ordered_keys:
            if key not in annotated_1080p:
                raise HTTPException(status_code=400, detail=f"缺少标注图: {key}")

        saved_dir = save_debug_images(annotated_1080p, suspect_compressed)
        logger.info(f"[judge] 阶段5: 图片已保存至 {saved_dir}")

        annotated_list = [annotated_1080p[k] for k in ordered_keys]
        logger.debug("[judge] 阶段5准备就绪: 3张标注图 + 1张嫌疑图")

        # ── 6. 获取自定义系统提示词并调用 LLM ──
        system_prompt = await get_system_prompt(db)
        logger.debug(f"[judge] 系统提示词长度: {len(system_prompt)}")

        client = VisionClient(
            model=settings.judge_model,
            base_url=settings.judge_base_url,
            api_key=settings.judge_api_key,
        )
        result = await client.judge_violation(
            annotated_images=annotated_list,
            suspect_image=suspect_compressed,
            system_prompt=system_prompt,
        )
        logger.debug(
            f"[judge] 阶段5完成: violated={result.violated}, reason={result.reason}"
        )

        # ── 7. 保存判定结果到数据库 ──
        record = JudgeRecord(
            image_id=image_id,
            violated=result.violated,
            reason=result.reason,
        )
        db.add(record)
        logger.debug("[judge] 判定结果已保存到数据库")

        logger.debug("[judge] ========== 判定请求完成 ==========")
        return Response(
            data=JudgeData(
                image_id=image_id,
                violated=result.violated,
                reason=result.reason,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[judge] 判定失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
