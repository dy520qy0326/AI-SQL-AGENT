import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import clear_all_cache
from app.ai.client import AIServiceError
from app.ai.service import (
    _get_lock,
    complete_comments,
    complete_relations,
)
from app.config import settings
from app.db.engine import get_db
from app.db.models import AICache
from app.schemas.ai import (
    AIStatusResponse,
    CacheClearResponse,
    CompleteCommentsResponse,
    CompleteRelationsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/projects/{project_id}/ai/complete-relations", response_model=CompleteRelationsResponse)
async def ai_complete_relations(project_id: str, db: AsyncSession = Depends(get_db)):
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI service is disabled")

    lock = _get_lock(project_id)
    if lock.locked():
        raise HTTPException(status_code=409, detail="AI request already in progress for this project")

    async with lock:
        try:
            result = await complete_relations(project_id, db)
            await db.commit()
            return result
        except AIServiceError as e:
            await db.rollback()
            raise HTTPException(status_code=503, detail=str(e))


@router.post("/projects/{project_id}/ai/complete-comments", response_model=CompleteCommentsResponse)
async def ai_complete_comments(project_id: str, db: AsyncSession = Depends(get_db)):
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI service is disabled")

    lock = _get_lock(project_id)
    if lock.locked():
        raise HTTPException(status_code=409, detail="AI request already in progress for this project")

    async with lock:
        try:
            result = await complete_comments(project_id, db)
            await db.commit()
            return result
        except AIServiceError as e:
            await db.rollback()
            raise HTTPException(status_code=503, detail=str(e))


@router.get("/projects/{project_id}/ai/status", response_model=AIStatusResponse)
async def ai_status(project_id: str, db: AsyncSession = Depends(get_db)):
    cache_count = (await db.execute(select(func.count(AICache.id)))).scalar() or 0
    return AIStatusResponse(
        ai_enabled=settings.ai_enabled,
        ai_model=settings.ai_model,
        cache_count=cache_count,
        last_completion=None,
    )


@router.post("/ai/cache/clear", response_model=CacheClearResponse)
async def ai_cache_clear(db: AsyncSession = Depends(get_db)):
    count = await clear_all_cache(db)
    await db.commit()
    return CacheClearResponse(deleted_count=count, message=f"cleared {count} cache entries")
