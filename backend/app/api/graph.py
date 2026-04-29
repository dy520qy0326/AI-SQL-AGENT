from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.schemas.graph import GraphResponse
from app.store.repository import Repository
from app.viz.graph import build_graph
from app.viz.mermaid import build_mermaid

router = APIRouter(prefix="/api/projects", tags=["graph"])


@router.get("/{project_id}/graph", response_model=GraphResponse)
async def get_graph(
    project_id: str,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    type: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    nodes, edges = await build_graph(project_id, db, min_confidence=min_confidence, type_filter=type)
    return GraphResponse(nodes=nodes, edges=edges)


@router.get("/{project_id}/mermaid", response_class=PlainTextResponse)
async def get_mermaid(
    project_id: str,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return await build_mermaid(project_id, db, min_confidence=min_confidence)
