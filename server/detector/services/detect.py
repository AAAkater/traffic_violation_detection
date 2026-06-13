"""检测业务逻辑 — 图片上传、YOLO 检测、结果持久化。"""

import io
import uuid

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.storage import S3Storage
from detector.models.detect import DetectData, DetectionItem
from detector.pipelines.detect import detect_pipeline
from detector.repositories.detect import DetectImageRepo, DetectionBoxRepo
from detector.settings import settings
from detector.utils import logger
from detector.utils.image_tools import preprocess_single


class DetectService:
    """检测业务逻辑服务。"""

    def __init__(self, session: AsyncSession, s3: S3Storage) -> None:
        self._session = session
        self._s3 = s3
        self._image_repo = DetectImageRepo(session)
        self._box_repo = DetectionBoxRepo(session)

    async def detect(self, contents: bytes, filename: str | None) -> DetectData:
        """执行检测流水线：上传图片 → 预处理 → YOLO 检测 → 保存结果。

        Args:
            contents: 图片二进制数据。
            filename: 原始文件名。

        Returns:
            DetectData 包含 image_id 和检测框列表。
        """
        logger.debug("[detect] ========== 开始检测请求 ==========")
        logger.debug(f"[detect] 文件名: {filename}, 大小: {len(contents)} bytes")

        # ── 0. 生成图片唯一标识 & 上传原始图片到对象存储 ──
        image_id = uuid.uuid4().hex[:16]
        object_key = self._s3.upload_bytes(
            data=contents,
            filename=filename,
            prefix="detect",
        )
        logger.info(f"[detect] 原始图片已上传: {object_key}")

        # ── 1. 预处理：裁剪象限 ──
        img = Image.open(io.BytesIO(contents))
        quadrants = preprocess_single(img)
        logger.debug(f"[detect] 裁剪出 {len(quadrants)} 个象限")

        # ── 2. YOLO 检测 ──
        detect_quadrants = {k: v for k, v in quadrants.items() if k in ("top_left", "top_right", "bottom_left")}
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
        from detector.db.tables import DetectImage, DetectionBox

        safe_filename = filename or "upload"
        await self._image_repo.create(
            DetectImage(
                image_id=image_id,
                filename=safe_filename,
                object_key=object_key,
            )
        )
        for item in items:
            await self._box_repo.create(
                DetectionBox(
                    image_id=image_id,
                    quadrant=item.quadrant,
                    bbox=item.bbox,
                    confidence=item.confidence,
                    class_name=item.class_name,
                )
            )

        logger.debug(f"[detect] 检测完成, 共 {len(items)} 个检测框")
        logger.debug("[detect] ========== 检测请求完成 ==========")

        return DetectData(
            image_id=image_id,
            detections=items,
        )
