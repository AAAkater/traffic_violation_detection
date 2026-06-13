"""依赖注入 — 集中管理 FastAPI 依赖项。"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from detector.db.engine import get_db
from detector.db.storage import S3Storage, s3_storage
from detector.services.detect import DetectService
from detector.services.history import HistoryService
from detector.services.judge import JudgeService
from detector.services.prompt import PromptService
from detector.services.provider import ProviderService

# ── 数据库会话 ──────────────────────────────────────────
SessionDep = Annotated[AsyncSession, Depends(get_db)]

# ── S3 存储 ──────────────────────────────────────────────
S3Dep = Annotated[S3Storage, Depends(lambda: s3_storage)]


# ── 服务工厂函数 ─────────────────────────────────────────
async def _get_detect_service(session: SessionDep, s3: S3Dep) -> DetectService:
    return DetectService(session=session, s3=s3)


async def _get_history_service(session: SessionDep, s3: S3Dep) -> HistoryService:
    return HistoryService(session=session, s3=s3)


async def _get_judge_service(session: SessionDep, s3: S3Dep) -> JudgeService:
    return JudgeService(session=session, s3=s3)


async def _get_prompt_service(session: SessionDep) -> PromptService:
    return PromptService(session=session)


async def _get_provider_service(session: SessionDep) -> ProviderService:
    return ProviderService(session=session)


# ── 业务服务依赖 ─────────────────────────────────────────
DetectServiceDep = Annotated[DetectService, Depends(_get_detect_service)]
HistoryServiceDep = Annotated[HistoryService, Depends(_get_history_service)]
JudgeServiceDep = Annotated[JudgeService, Depends(_get_judge_service)]
PromptServiceDep = Annotated[PromptService, Depends(_get_prompt_service)]
ProviderServiceDep = Annotated[ProviderService, Depends(_get_provider_service)]
