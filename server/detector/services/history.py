"""历史记录查询业务逻辑。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.tables import DetectImage, DetectionBox, JudgeRecord
from detector.models.history import (
    HistoryBoxItem,
    HistoryItem,
    HistoryJudgeItem,
    HistoryPage,
)
from detector.repositories.detect import DetectImageRepo, DetectionBoxRepo
from detector.repositories.judge import JudgeRecordRepo


class HistoryService:
    """历史记录查询业务逻辑服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._image_repo = DetectImageRepo(session)
        self._box_repo = DetectionBoxRepo(session)
        self._judge_repo = JudgeRecordRepo(session)

    async def get_history(self, page: int, page_size: int) -> HistoryPage:
        """分页查询上传历史，包含图片链接、检测框坐标和 LLM 判定结果。

        Args:
            page: 页码，从 1 开始。
            page_size: 每页条数。

        Returns:
            HistoryPage 分页数据。
        """
        # ── 1. 查总数 ──
        count_stmt = select(func.count(DetectImage.image_id))
        total = (await self._session.execute(count_stmt)).scalar_one()

        # ── 2. 分页查 DetectImage ──
        offset = (page - 1) * page_size
        images_stmt = select(DetectImage).order_by(DetectImage.created_at.desc()).offset(offset).limit(page_size)
        images = list((await self._session.execute(images_stmt)).scalars().all())

        if not images:
            return HistoryPage(
                items=[],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

        image_ids = [img.image_id for img in images]

        # ── 3. 批量查 DetectionBox ──
        boxes = await self._box_repo.list_by_image_ids(image_ids)
        boxes_by_image: dict[str, list[DetectionBox]] = {}
        for b in boxes:
            boxes_by_image.setdefault(b.image_id, []).append(b)

        # ── 4. 批量查 JudgeRecord ──
        judges = await self._judge_repo.list_by_image_ids(image_ids)
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
                    provider_id=judge_rec.provider_id,
                    model=judge_rec.model,
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

        return HistoryPage(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
