import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIServiceError, ai_client
from app.config import settings
from app.db.engine import get_db
from app.nl.context import build_context
from app.schemas.ask import AskRequest, AskSource, AskSyncResponse
from app.store.repository import Repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["nl-query"])


def _extract_sources(text: str) -> list[AskSource]:
    """Extract source citations from AI response."""
    sources: list[AskSource] = []
    m = re.search(r"```sources\s*([\s\S]*?)```", text)
    if m:
        try:
            raw = json.loads(m.group(1))
            for item in raw:
                sources.append(AskSource(
                    table=item.get("table", ""),
                    column=item.get("column"),
                    description=item.get("description"),
                ))
        except json.JSONDecodeError:
            pass
    return sources


def _strip_sources_block(text: str) -> str:
    """Remove the sources JSON block from the response text."""
    return re.sub(r"```sources[\s\S]*?```", "", text).strip()


@router.post("/projects/{project_id}/ask")
async def ask_stream(project_id: str, body: AskRequest, db: AsyncSession = Depends(get_db)):
    """Ask a question about the database schema, streaming SSE response."""
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI service is disabled")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    repo = Repository(db)

    # Create or reuse session
    session_id = body.session_id
    if session_id:
        session = await repo.get_session(session_id)
        if session is None or session.project_id != project_id:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        title = body.question[:50] if len(body.question) > 50 else body.question
        session = await repo.create_session(project_id, title=title)
        await db.flush()
        session_id = session.id

    # Build context
    ctx = await build_context(db, project_id, body.question, session_id)
    logger.info("NL query mode=%s, token_estimate=%d, tables=%s", ctx.mode, ctx.token_estimate, ctx.candidate_tables)

    # Store user message
    await repo.add_message(session_id, "user", body.question)
    await db.flush()

    async def sse_generator():
        full_response = ""
        try:
            for chunk in ai_client.complete_stream(ctx.system_prompt, ctx.user_message):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Extract sources and strip from response
            sources = _extract_sources(full_response)
            clean_response = _strip_sources_block(full_response)

            # Store assistant message
            sources_data = [s.model_dump() for s in sources] if sources else None
            await repo.add_message(session_id, "assistant", clean_response, sources_data)
            await db.commit()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except AIServiceError as e:
            logger.error("NL ask stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )


@router.post("/projects/{project_id}/ask/sync", response_model=AskSyncResponse)
async def ask_sync(project_id: str, body: AskRequest, db: AsyncSession = Depends(get_db)):
    """Ask a question about the database schema, synchronous response."""
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI service is disabled")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    repo = Repository(db)

    # Create or reuse session
    session_id = body.session_id
    if session_id:
        session = await repo.get_session(session_id)
        if session is None or session.project_id != project_id:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        title = body.question[:50] if len(body.question) > 50 else body.question
        session = await repo.create_session(project_id, title=title)
        await db.flush()
        session_id = session.id

    # Build context
    ctx = await build_context(db, project_id, body.question, session_id)

    # Store user message
    await repo.add_message(session_id, "user", body.question)
    await db.flush()

    try:
        response_text = await _run_async(ai_client.complete, ctx.system_prompt, ctx.user_message)
    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))

    sources = _extract_sources(response_text)
    clean_response = _strip_sources_block(response_text)

    sources_data = [s.model_dump() for s in sources] if sources else None
    await repo.add_message(session_id, "assistant", clean_response, sources_data)
    await db.commit()

    return AskSyncResponse(answer=clean_response, sources=sources, session_id=session_id)


async def _run_async(func, *args, **kwargs):
    import asyncio
    return await asyncio.to_thread(func, *args, **kwargs)
