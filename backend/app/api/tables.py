from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.schemas.table import (
    ColumnResponse,
    ForeignKeyResponse,
    IndexResponse,
    TableDetailResponse,
    TableResponse,
)
from app.store.repository import Repository

router = APIRouter(prefix="/api/projects", tags=["tables"])


@router.get("/{project_id}/tables", response_model=list[TableResponse])
async def list_tables(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tables = await repo.get_tables(project_id)
    return [
        TableResponse(
            id=t.id,
            name=t.name,
            schema_name=t.schema_name,
            comment=t.comment,
            column_count=len(t.columns) if t.columns else 0,
            created_at=t.created_at,
        )
        for t in tables
    ]


@router.get("/{project_id}/tables/{table_id}", response_model=TableDetailResponse)
async def get_table(project_id: str, table_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    table = await repo.get_table_detail(table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")
    if table.project_id != project_id:
        raise HTTPException(status_code=404, detail="Table not found in this project")

    return TableDetailResponse(
        id=table.id,
        name=table.name,
        schema_name=table.schema_name,
        comment=table.comment,
        columns=[
            ColumnResponse(
                id=c.id,
                name=c.name,
                data_type=c.data_type,
                length=c.length,
                nullable=c.nullable,
                default_value=c.default_value,
                is_primary_key=c.is_primary_key,
                ordinal_position=c.ordinal_position,
                comment=c.comment,
            )
            for c in (table.columns or [])
        ],
        indexes=[
            IndexResponse(id=idx.id, name=idx.name, unique=idx.unique, columns=idx.columns)
            for idx in (table.indexes or [])
        ],
        foreign_keys=[
            ForeignKeyResponse(
                id=fk.id,
                columns=fk.columns,
                ref_table_name=fk.ref_table_name,
                ref_columns=fk.ref_columns,
                constraint_name=fk.constraint_name,
            )
            for fk in (table.foreign_keys or [])
        ],
        created_at=table.created_at,
    )
