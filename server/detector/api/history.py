"""上传历史查询端点 — 分页查询检测记录，包含图片链接、LLM 回复、检测框坐标。"""

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from detector.common.response import (
    HistoryBoxItem,
    HistoryItem,
    HistoryJudgeItem,
    HistoryPage,
    Response,
)
from detector.db import DetectImage, DetectionBox, JudgeRecord, SessionDep

router = APIRouter(tags=["history"])


@router.get("/history")
async def get_history(
    db: SessionDep,
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
) -> Response[HistoryPage]:
    """分页查询上传历史，包含图片链接、检测框坐标和 LLM 判定结果。"""
    # ── 1. 查总数 ──
    count_stmt = select(func.count(DetectImage.image_id))
    total = (await db.execute(count_stmt)).scalar_one()

    # ── 2. 分页查 DetectImage ──
    offset = (page - 1) * page_size
    images_stmt = select(DetectImage).order_by(DetectImage.created_at.desc()).offset(offset).limit(page_size)
    images = list((await db.execute(images_stmt)).scalars().all())

    if not images:
        return Response(
            data=HistoryPage(
                items=[],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=0,
            )
        )

    image_ids = [img.image_id for img in images]

    # ── 3. 批量查 DetectionBox ──
    boxes_stmt = select(DetectionBox).where(DetectionBox.image_id.in_(image_ids))
    boxes = list((await db.execute(boxes_stmt)).scalars().all())
    boxes_by_image: dict[str, list[DetectionBox]] = {}
    for b in boxes:
        boxes_by_image.setdefault(b.image_id, []).append(b)

    # ── 4. 批量查 JudgeRecord ──
    judge_stmt = select(JudgeRecord).where(JudgeRecord.image_id.in_(image_ids))
    judges = list((await db.execute(judge_stmt)).scalars().all())
    judge_by_image: dict[str, JudgeRecord] = {j.image_id: j for j in judges}

    # ── 5. 组装结果 ──
    total_pages = (total + page_size - 1) // page_size
    items: list[HistoryItem] = []
    for img in images:
        box_items = [
            HistoryBoxItem(
                quadrant=b.quadrant,
                bbox=b.bbox,
                confidence=b.confidence,
                class_name=b.class_name,
            )
            for b in boxes_by_image.get(img.image_id, [])
        ]
        judge_rec = judge_by_image.get(img.image_id)
        judge_item = (
            HistoryJudgeItem(
                violated=judge_rec.violated,
                reason=judge_rec.reason,
                prompt_name=judge_rec.prompt_name,
            )
            if judge_rec
            else None
        )
        items.append(
            HistoryItem(
                image_id=img.image_id,
                filename=img.filename,
                image_url=img.image_url,
                created_at=img.created_at.isoformat() if img.created_at else "",
                detections=box_items,
                judge=judge_item,
            )
        )

    return Response(
        data=HistoryPage(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )
