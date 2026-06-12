"""系统提示词端点 — 自定义 LLM 判定时使用的系统提示词，持久化到数据库。"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from detector.common.response import Response
from detector.db import SessionDep, SystemPrompt
from detector.settings import settings
from detector.utils import logger

router = APIRouter(tags=["prompt"])


@router.post("/prompt")
async def set_prompt(name: str, content: str, db: SessionDep) -> Response[dict[str, Any]]:
    """创建或更新系统提示词，并设为激活。

    Args:
        name: 提示词名称（唯一标识）。
        content: 提示词内容。
        db: 数据库会话。
    """
    # 将所有现有提示词设为非激活
    result = await db.execute(select(SystemPrompt).where(SystemPrompt.is_active.is_(True)))
    for old in result.scalars().all():
        old.is_active = False

    # 查找是否已存在同名提示词
    result = await db.execute(select(SystemPrompt).where(SystemPrompt.name == name))
    existing = result.scalar_one_or_none()

    if existing:
        existing.content = content
        existing.is_active = True
        existing.updated_at = datetime.now()
        logger.info(f"[prompt] 更新提示词: name={name}")
    else:
        prompt = SystemPrompt(name=name, content=content, is_active=True)
        db.add(prompt)
        logger.info(f"[prompt] 创建提示词: name={name}")

    return Response(
        msg="系统提示词已更新",
        data={"name": name, "content": content},
    )


@router.get("/prompt")
async def get_prompt(db: SessionDep) -> Response[dict[str, str]]:
    """获取当前激活的系统提示词。"""
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.is_active.is_(True)).order_by(SystemPrompt.updated_at.desc())
    )
    active = result.scalar_one_or_none()

    if active:
        return Response(data={"name": active.name, "content": active.content})
    return Response(data={"name": "default", "content": settings.default_system_prompt})


@router.get("/prompt/list")
async def list_prompts(db: SessionDep) -> Response[list[dict[str, Any]]]:
    """列出所有系统提示词。"""
    result = await db.execute(select(SystemPrompt).order_by(SystemPrompt.created_at.desc()))
    prompts = result.scalars().all()
    return Response(
        data=[
            {
                "name": p.name,
                "content": p.content,
                "is_active": p.is_active,
                "updated_at": str(p.updated_at),
            }
            for p in prompts
        ],
    )


async def get_system_prompt(db: AsyncSession) -> str:
    """获取当前生效的系统提示词（供 judge 端点调用）。"""
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.is_active.is_(True)).order_by(SystemPrompt.updated_at.desc())
    )
    active = result.scalar_one_or_none()
    if active and active.content:
        return active.content
    return settings.default_system_prompt
