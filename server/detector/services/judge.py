"""违法判定业务逻辑 — 图片下载、预处理、LLM 判定、结果持久化。"""

import io

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from detector.clients.vision import VisionClient
from detector.db.storage import S3Storage
from detector.models.detect import Detection
from detector.models.judge import JudgeData
from detector.repositories.detect import DetectImageRepo, DetectionBoxRepo
from detector.repositories.judge import JudgeRecordRepo
from detector.repositories.prompt import SystemPromptRepo
from detector.repositories.provider import ModelProviderRepo
from detector.settings import settings
from detector.utils import logger
from detector.utils.image_tools import (
    compress_to_1080p,
    preprocess_single,
    redraw_detections_on_compressed,
    save_debug_images,
)


class JudgeService:
    """违法判定业务逻辑服务。"""

    def __init__(self, session: AsyncSession, s3: S3Storage) -> None:
        self._session = session
        self._s3 = s3
        self._image_repo = DetectImageRepo(session)
        self._box_repo = DetectionBoxRepo(session)
        self._judge_repo = JudgeRecordRepo(session)
        self._prompt_repo = SystemPromptRepo(session)
        self._provider_repo = ModelProviderRepo(session)

    async def judge(self, image_id: str, provider_id: int, model: str) -> JudgeData:
        """执行违法判定流水线。

        Args:
            image_id: 检测接口返回的图片唯一标识。
            provider_id: 模型提供商 ID。
            model: 模型名称。

        Returns:
            JudgeData 包含判定结果。

        Raises:
            ValueError: 图片不存在、无 URL 或无检测框。
            RuntimeError: 未配置模型提供商。
        """
        logger.debug("[judge] ========== 开始判定请求 ==========")
        logger.debug(f"[judge] image_id: {image_id}")

        # ── 0. 从数据库获取原图信息和检测框 ──
        detect_image = await self._image_repo.get_by_image_id(image_id)
        if detect_image is None:
            raise ValueError(f"未找到图片: {image_id}")
        if not detect_image.image_url:
            raise ValueError(f"图片无对象存储 URL: {image_id}")

        detection_boxes = await self._box_repo.list_by_image_id(image_id)
        if not detection_boxes:
            raise ValueError(f"该图片无检测框: {image_id}")
        logger.debug(f"[judge] 从数据库获取: 原图={detect_image.image_url}, 检测框={len(detection_boxes)} 个")

        # ── 1. 从对象存储下载原图 ──
        logger.debug("[judge] 阶段1: 从对象存储下载原图...")
        contents = self._s3.download_image(detect_image.image_url)
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

        detect_quadrants = {k: v for k, v in quadrants.items() if k in ("top_left", "top_right", "bottom_left")}
        logger.debug(
            f"[judge] 阶段3完成: 检测象限={list(detect_quadrants.keys())}, 分组={list(per_quadrant_detections.keys())}"
        )

        # ── 4. 压缩到 1080P 并重绘检测框 ──
        logger.debug("[judge] 阶段4: 压缩象限到1080P并重绘检测框...")
        compressed_detect = {k: compress_to_1080p(v) for k, v in detect_quadrants.items()}
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
                raise ValueError(f"缺少标注图: {key}")

        saved_dir = save_debug_images(annotated_1080p, suspect_compressed)
        logger.info(f"[judge] 阶段5: 图片已保存至 {saved_dir}")

        annotated_list = [annotated_1080p[k] for k in ordered_keys]
        logger.debug("[judge] 阶段5准备就绪: 3张标注图 + 1张嫌疑图")

        # ── 6. 获取自定义系统提示词和模型提供商配置，调用 LLM ──
        system_prompt = await self._get_system_prompt()
        logger.debug(f"[judge] 系统提示词长度: {len(system_prompt)}")

        provider = await self._provider_repo.get_by_id(provider_id)
        if provider is None:
            raise RuntimeError(f"未找到模型提供商: {provider_id}")

        # 验证模型是否已激活
        activated_models = provider.activated_models or []
        if model not in activated_models:
            raise ValueError(f"模型 {model} 未激活，当前已激活模型: {activated_models or '无'}")

        client = VisionClient(
            model=model,
            base_url=provider.base_url,
            api_key=provider.api_key,
        )
        violated, reason, raw_response = await client.judge_violation(
            annotated_images=annotated_list,
            suspect_image=suspect_compressed,
            system_prompt=system_prompt,
        )
        logger.debug(f"[judge] 阶段5完成: violated={violated}, reason={reason}")

        # ── 7. 保存判定结果到数据库 ──
        from detector.db.tables import JudgeRecord

        record = JudgeRecord(
            image_id=image_id,
            violated=violated,
            reason=reason,
            provider_id=provider_id,
            model=model,
        )
        await self._judge_repo.create(record)
        logger.debug("[judge] 判定结果已保存到数据库")

        logger.debug("[judge] ========== 判定请求完成 ==========")
        return JudgeData(
            image_id=image_id,
            violated=violated,
            reason=reason,
            provider_id=provider_id,
            model=model,
        )

    async def _get_system_prompt(self) -> str:
        """获取当前生效的系统提示词。"""
        active = await self._prompt_repo.get_active()
        if active and active.content:
            return active.content
        return settings.default_system_prompt
