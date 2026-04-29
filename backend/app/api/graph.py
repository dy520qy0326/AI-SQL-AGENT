from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.schemas.graph import GraphResponse
from app.store.repository import Repository
from app.viz.graph import build_graph
from app.viz.mermaid import build_mermaid

router = APIRouter(prefix="/api/projects", tags=["graph"])


def _parse_table_ids(raw: str | None) -> set[str] | None:
    """Parse comma-separated table_ids query param into a set, or None."""
    if not raw or not raw.strip():
        return None
    return {tid.strip() for tid in raw.split(",") if tid.strip()}


@router.get("/{project_id}/graph", response_model=GraphResponse)
async def get_graph(
    project_id: str,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    type: str | None = Query(None, alias="type"),
    table_ids: str | None = Query(None, alias="table_ids"),
    db: AsyncSession = Depends(get_db),
):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tids = _parse_table_ids(table_ids)
    nodes, edges = await build_graph(project_id, db, min_confidence=min_confidence, type_filter=type, table_ids=tids)
    return GraphResponse(nodes=nodes, edges=edges)


@router.get("/{project_id}/mermaid", response_class=PlainTextResponse)
async def get_mermaid(
    project_id: str,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    table_ids: str | None = Query(None, alias="table_ids"),
    db: AsyncSession = Depends(get_db),
):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tids = _parse_table_ids(table_ids)
    return await build_mermaid(project_id, db, min_confidence=min_confidence, table_ids=tids)
