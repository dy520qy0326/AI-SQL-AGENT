from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.schemas.relation import RelationListResponse, RelationResponse
from app.store.repository import Repository

router = APIRouter(prefix="/api/projects", tags=["relations"])


@router.get("/{project_id}/relations", response_model=RelationListResponse)
async def list_relations(
    project_id: str,
    type: str | None = Query(None, alias="type"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all tables for name resolution
    tables = await repo.get_tables(project_id)
    tmap = {t.id: t.name for t in tables}

    relations = await repo.get_relations(project_id, type_filter=type, min_confidence=min_confidence)
    items = [
        RelationResponse(
            id=r.id,
            source_table_id=r.source_table_id,
            source_table_name=tmap.get(r.source_table_id, ""),
            source_columns=r.source_columns,
            target_table_id=r.target_table_id,
            target_table_name=tmap.get(r.target_table_id, ""),
            target_columns=r.target_columns,
            relation_type=r.relation_type,
            confidence=r.confidence,
            source=r.source,
        )
        for r in relations
    ]
    return RelationListResponse(items=items, total=len(items))
