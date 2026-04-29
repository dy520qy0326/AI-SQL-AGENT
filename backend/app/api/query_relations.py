from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.query_relation.parser import DiscoveredRelation, parse_join_relations
from app.schemas.query_relation import (
    QueryRelationPreview,
    QueryRelationRequest,
    QueryRelationResponse,
    SaveRelationItem,
    SaveRelationRequest,
    SaveRelationResponse,
)
from app.store.repository import RelationData, Repository

router = APIRouter(prefix="/api/projects/{project_id}/query-relations", tags=["query-relations"])


@router.post("", response_model=QueryRelationResponse)
async def preview_query_relations(
    project_id: str,
    body: QueryRelationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse SQL query text and preview discovered table relations (not saved)."""
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tables_dict = await repo.get_project_tables_dict(project_id)
    dialect = project_info.get("dialect", "mysql")

    try:
        relations, unmatched, query_count = parse_join_relations(
            body.sql, tables_dict, dialect=dialect
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    items = []
    for r in relations:
        src_tid = _table_id(tables_dict, r.source_table)
        tgt_tid = _table_id(tables_dict, r.target_table)
        exists = False
        if src_tid and tgt_tid:
            exists = await repo.relation_exists(
                project_id, src_tid, tgt_tid, r.source_columns, r.target_columns
            )
        items.append(
            QueryRelationPreview(
                temp_id=r.temp_id,
                source_table=r.source_table,
                source_columns=r.source_columns,
                target_table=r.target_table,
                target_columns=r.target_columns,
                join_type=r.join_type,
                confidence=r.confidence,
                already_exists=exists,
            )
        )

    return QueryRelationResponse(
        dialect=dialect,
        queries_parsed=query_count,
        relations=items,
        unmatched_tables=unmatched,
    )


@router.post("/save", response_model=SaveRelationResponse)
async def save_query_relations(
    project_id: str,
    body: SaveRelationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save user-confirmed query-derived relations to the database."""
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tables_dict = await repo.get_project_tables_dict(project_id)
    dialect = project_info.get("dialect", "mysql")

    try:
        relations, unmatched, _ = parse_join_relations(
            body.sql, tables_dict, dialect=dialect
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build lookup by temp_id
    rel_map = {r.temp_id: r for r in relations}

    # Validate all requested temp_ids
    invalid_ids = [rid for rid in body.relation_ids if rid not in rel_map]
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation_ids: {invalid_ids}",
        )

    # Convert selected relations to RelationData, skipping unmatched tables
    to_save: list[RelationData] = []
    for rid in body.relation_ids:
        dr = rel_map[rid]
        src_tid = _table_id(tables_dict, dr.source_table)
        tgt_tid = _table_id(tables_dict, dr.target_table)
        if src_tid is None or tgt_tid is None:
            continue
        to_save.append(
            RelationData(
                source_table_id=src_tid,
                source_columns=dr.source_columns,
                target_table_id=tgt_tid,
                target_columns=dr.target_columns,
                relation_type="QUERY_INFERRED",
                confidence=dr.confidence,
                source=f"query: {body.sql[:200]}",
            )
        )

    saved = await repo.save_query_relations(project_id, to_save)
    await db.commit()
    skipped = len(to_save) - len(saved)

    tmap = {t.id: t.name for t in tables_dict.values()}
    items = [
        SaveRelationItem(
            id=r.id,
            source_table=tmap.get(r.source_table_id, ""),
            source_columns=r.source_columns,
            target_table=tmap.get(r.target_table_id, ""),
            target_columns=r.target_columns,
            relation_type=r.relation_type,
            confidence=r.confidence,
        )
        for r in saved
    ]

    return SaveRelationResponse(
        saved=len(saved),
        skipped=skipped,
        relations=items,
    )


def _table_id(tables_dict: dict, table_name: str) -> str | None:
    """Look up a table's ID by name (case-insensitive)."""
    t = tables_dict.get(table_name.lower())
    return t.id if t else None
