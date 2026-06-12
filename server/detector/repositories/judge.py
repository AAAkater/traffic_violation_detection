"""判定记录的数据访问层。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.tables import JudgeRecord


class JudgeRecordRepo:
    """判定记录数据仓库。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_image_id(self, image_id: str) -> JudgeRecord | None:
        """根据 image_id 查询判定记录。"""
        result = await self._session.execute(select(JudgeRecord).where(JudgeRecord.image_id == image_id))
        return result.scalar_one_or_none()

    async def list_by_image_ids(self, image_ids: list[str]) -> list[JudgeRecord]:
        """根据多个 image_id 批量查询判定记录。"""
        result = await self._session.execute(select(JudgeRecord).where(JudgeRecord.image_id.in_(image_ids)))
        return list(result.scalars().all())

    async def create(self, record: JudgeRecord) -> JudgeRecord:
        """创建判定记录。"""
        self._session.add(record)
        return record
