from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.db.models import ConversationMessage, ConversationSession
from app.schemas.session import (
    MessageListResponse,
    MessageResponse,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
)
from app.store.repository import Repository

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions", status_code=201, response_model=SessionResponse)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    session = await repo.create_session(body.project_id, title=body.title)
    await db.commit()
    return SessionResponse(
        id=session.id,
        project_id=session.project_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/projects/{project_id}/sessions", response_model=SessionListResponse)
async def list_project_sessions(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project = await repo.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    sessions = await repo.list_project_sessions(project_id)

    items = []
    for s in sessions:
        count_q = select(func.count(ConversationMessage.id)).where(
            ConversationMessage.session_id == s.id
        )
        msg_count = (await db.execute(count_q)).scalar() or 0
        items.append(SessionResponse(
            id=s.id,
            project_id=s.project_id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=msg_count,
        ))

    return SessionListResponse(items=items, total=len(items))


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    session = await repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = await repo.get_messages(session_id)
    items = [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            sources=m.sources,
            created_at=m.created_at,
        )
        for m in msgs
    ]
    return MessageListResponse(items=items, total=len(items))


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    deleted = await repo.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.commit()
