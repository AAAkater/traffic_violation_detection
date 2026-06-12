"""检测图片与检测框的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.tables import DetectImage, DetectionBox


class DetectImageRepo:
    """检测原图数据仓库。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_image_id(self, image_id: str) -> DetectImage | None:
        """根据 image_id 查询检测原图。"""
        result = await self._session.execute(select(DetectImage).where(DetectImage.image_id == image_id))
        return result.scalar_one_or_none()

    async def create(self, image: DetectImage) -> DetectImage:
        """创建检测原图记录。"""
        self._session.add(image)
        return image


class DetectionBoxRepo:
    """检测框数据仓库。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_image_id(self, image_id: str) -> list[DetectionBox]:
        """根据 image_id 查询所有检测框。"""
        result = await self._session.execute(select(DetectionBox).where(DetectionBox.image_id == image_id))
        return list(result.scalars().all())

    async def list_by_image_ids(self, image_ids: list[str]) -> list[DetectionBox]:
        """根据多个 image_id 批量查询检测框。"""
        result = await self._session.execute(select(DetectionBox).where(DetectionBox.image_id.in_(image_ids)))
        return list(result.scalars().all())

    async def create(self, box: DetectionBox) -> DetectionBox:
        """创建检测框记录。"""
        self._session.add(box)
        return box

    async def create_batch(self, boxes: list[DetectionBox]) -> list[DetectionBox]:
        """批量创建检测框记录。"""
        self._session.add_all(boxes)
        return boxes
