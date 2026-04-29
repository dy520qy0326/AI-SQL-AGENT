import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.db.models import Project
from app.detector.relation import detect_relations
from app.parser import MySQLParser, PostgreSQLParser, ParseResult
from app.schemas.project import (
    ErrorItem,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    UploadRequest,
    UploadResponse,
)
from app.store.repository import RelationData, Repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


def _parse_sql(sql_content: str, dialect: str | None = None) -> tuple[ParseResult, str]:
    """Pick the right parser and parse the SQL. Returns (result, actual_dialect)."""
    if dialect and dialect.lower() == "postgresql":
        parser = PostgreSQLParser()
        result = parser.parse(sql_content)
        return result, result.dialect
    else:
        parser = MySQLParser()
        result = parser.parse(sql_content)
        return result, result.dialect


@router.post("", status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project = await repo.create_project(
        name=body.name,
        description=body.description,
        dialect=body.dialect,
    )
    await db.commit()
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "dialect": project.dialect,
        "table_count": 0,
        "relation_count": 0,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


@router.get("", response_model=ProjectListResponse)
async def list_projects(page: int = 1, size: int = 12, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    items, total = await repo.list_projects(page=page, size=size)
    return ProjectListResponse(
        items=[ProjectResponse(**item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    info = await repo.get_project(project_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**info)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    deleted = await repo.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.commit()


@router.post("/{project_id}/upload", response_model=UploadResponse)
async def upload_sql(project_id: str, body: UploadRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Parse
    dialect = project_info.get("dialect", "") or ""
    parse_result, actual_dialect = _parse_sql(body.sql_content, dialect)
    errors = [
        ErrorItem(statement_index=e.statement_index, line=e.line, message=e.message)
        for e in parse_result.errors
    ]

    # If no tables and has errors → 422 (before any DB writes)
    if not parse_result.tables and errors:
        raise HTTPException(status_code=422, detail=[e.model_dump() for e in errors])

    # Update project dialect if auto-detected
    if dialect == "" and parse_result.dialect:
        await db.execute(
            update(Project).where(Project.id == project_id).values(dialect=actual_dialect)
        )

    # Save tables
    await repo.save_parse_result(project_id, parse_result)

    # Run relation detection
    relations = await detect_relations(project_id, db)
    await repo.save_relations(project_id, relations)
    await db.commit()

    return UploadResponse(
        tables_count=len(parse_result.tables),
        relations_count=len(relations),
        errors=errors,
    )
