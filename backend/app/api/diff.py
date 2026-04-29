import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIServiceError, ai_client
from app.config import settings
from app.db.engine import get_db
from app.diff.engine import compute_diff
from app.diff.migration import generate_alter_scripts
from app.parser import MySQLParser, PostgreSQLParser
from app.schemas.version import (
    DiffListResponse,
    DiffRequest,
    DiffResponse,
    VersionCreateRequest,
    VersionListResponse,
    VersionResponse,
)
from app.store.repository import Repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects/{project_id}", tags=["versions"])


def _parse_sql(sql_content: str, dialect: str | None = None) -> tuple[dict, str]:
    """Parse SQL and return (parse_result_dict, actual_dialect)."""
    if dialect and dialect.lower() == "postgresql":
        parser = PostgreSQLParser()
    else:
        parser = MySQLParser()

    result = parser.parse(sql_content)
    return result.model_dump(), result.dialect


def _table_list(parse_result: dict) -> list[dict]:
    """Extract tables list from parse_result dict, normalizing empty."""
    tables = parse_result.get("tables", [])
    if not tables:
        # If the parse_result has the ORM-style structure
        tables = parse_result.get("tables", [])
    return tables


# ── Version endpoints ────────────────────────────────────────────────


@router.post("/versions", status_code=201)
async def create_version(project_id: str, body: VersionCreateRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Parse SQL
    dialect = project_info.get("dialect", "") or ""
    parse_result_dict, actual_dialect = _parse_sql(body.sql_content, dialect)

    # Calculate hash
    file_hash = hashlib.sha256(body.sql_content.encode()).hexdigest()

    # Save version
    version = await repo.create_version(
        project_id=project_id,
        version_tag=body.version_tag,
        file_hash=file_hash,
        parse_result=parse_result_dict,
    )
    await db.commit()

    tables = _table_list(parse_result_dict)
    return VersionResponse(
        id=version.id,
        project_id=version.project_id,
        version_tag=version.version_tag,
        file_hash=version.file_hash,
        tables_count=len(tables),
        created_at=version.created_at.isoformat() if version.created_at else None,
    )


@router.get("/versions", response_model=VersionListResponse)
async def list_versions(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    versions = await repo.list_versions(project_id)
    items = [
        VersionResponse(
            id=v.id,
            project_id=v.project_id,
            version_tag=v.version_tag,
            file_hash=v.file_hash,
            tables_count=len(v.parse_result.get("tables", [])),
            created_at=v.created_at.isoformat() if v.created_at else None,
        )
        for v in versions
    ]
    return VersionListResponse(items=items, total=len(items))


@router.delete("/versions/{version_id}", status_code=204)
async def delete_version(project_id: str, version_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    version = await repo.get_version(version_id)
    if version is None or version.project_id != project_id:
        raise HTTPException(status_code=404, detail="Version not found")

    await repo.delete_version(version_id)
    await db.commit()


# ── Diff endpoints ───────────────────────────────────────────────────


@router.post("/diff", status_code=201, response_model=DiffResponse)
async def create_diff(project_id: str, body: DiffRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    old = await repo.get_version(body.old_version_id)
    new = await repo.get_version(body.new_version_id)

    if old is None or new is None:
        raise HTTPException(status_code=404, detail="Version not found")
    if old.project_id != project_id or new.project_id != project_id:
        raise HTTPException(status_code=404, detail="Version does not belong to this project")

    old_tables = _table_list(old.parse_result)
    new_tables = _table_list(new.parse_result)

    result = compute_diff(old_tables, new_tables)

    diff_data = {
        "tables_added": result.tables_added,
        "tables_removed": result.tables_removed,
        "tables_renamed": result.tables_renamed,
        "fields_added": result.fields_added,
        "fields_removed": result.fields_removed,
        "fields_modified": result.fields_modified,
        "fields_renamed": result.fields_renamed,
        "indexes_added": result.indexes_added,
        "indexes_removed": result.indexes_removed,
        "relations_added": result.relations_added,
        "relations_removed": result.relations_removed,
        "breaking_changes": result.breaking_changes,
        "breaking_details": result.breaking_details,
        "summary_stats": result.summary_stats,
    }

    diff = await repo.create_diff(
        project_id=project_id,
        old_version_id=body.old_version_id,
        new_version_id=body.new_version_id,
        diff_data=diff_data,
        breaking_changes=result.breaking_changes,
    )
    await db.commit()

    return DiffResponse(
        id=diff.id,
        project_id=diff.project_id,
        old_version_id=diff.old_version_id,
        new_version_id=diff.new_version_id,
        diff_data=diff_data,
        summary=diff.summary,
        breaking_changes=diff.breaking_changes,
        created_at=diff.created_at.isoformat() if diff.created_at else None,
    )


@router.get("/diff/{diff_id}", response_model=DiffResponse)
async def get_diff(project_id: str, diff_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    diff = await repo.get_diff(diff_id)
    if diff is None or diff.project_id != project_id:
        raise HTTPException(status_code=404, detail="Diff not found")

    return DiffResponse(
        id=diff.id,
        project_id=diff.project_id,
        old_version_id=diff.old_version_id,
        new_version_id=diff.new_version_id,
        diff_data=diff.diff_data,
        summary=diff.summary,
        breaking_changes=diff.breaking_changes,
        created_at=diff.created_at.isoformat() if diff.created_at else None,
    )


@router.get("/diffs", response_model=DiffListResponse)
async def list_diffs(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise HTTPException(status_code=404, detail="Project not found")

    diffs = await repo.list_diffs(project_id)
    items = [
        DiffResponse(
            id=d.id,
            project_id=d.project_id,
            old_version_id=d.old_version_id,
            new_version_id=d.new_version_id,
            diff_data=d.diff_data,
            summary=d.summary,
            breaking_changes=d.breaking_changes,
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in diffs
    ]
    return DiffListResponse(items=items, total=len(items))


# ── AI summary endpoint ──────────────────────────────────────────────


@router.post("/diff/{diff_id}/ai-summary")
async def diff_ai_summary(project_id: str, diff_id: str, db: AsyncSession = Depends(get_db)):
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI service is disabled")

    repo = Repository(db)
    diff = await repo.get_diff(diff_id)
    if diff is None or diff.project_id != project_id:
        raise HTTPException(status_code=404, detail="Diff not found")

    # Build prompt from diff_data
    diff_data = diff.diff_data
    stats = diff_data.get("summary_stats", {})

    prompt_parts = [f"Analyze the following schema changes between two versions of a database."]
    prompt_parts.append(f"\n## Summary Statistics")
    for category, counts in stats.items():
        prompt_parts.append(f"{category}: {json.dumps(counts, ensure_ascii=False)}")

    prompt_parts.append(f"\n## Breaking Changes ({len(diff_data.get('breaking_details', []))})")
    for b in diff_data.get("breaking_details", []):
        prompt_parts.append(f"- {b}")

    prompt_parts.append(f"\n## Tables Added ({len(diff_data.get('tables_added', []))})")
    for t in diff_data.get("tables_added", []):
        cols = ", ".join(c["name"] for c in t.get("columns", []))
        prompt_parts.append(f"- {t['name']}: {cols}")

    prompt_parts.append(f"\n## Tables Removed ({len(diff_data.get('tables_removed', []))})")
    for t in diff_data.get("tables_removed", []):
        prompt_parts.append(f"- {t['name']}")

    prompt_parts.append(f"\n## Fields Modified ({len(diff_data.get('fields_modified', []))})")
    for f in diff_data.get("fields_modified", []):
        ch = f.get("changes", {})
        descs = []
        for attr, vals in ch.items():
            descs.append(f"{attr}: {vals.get('before')}→{vals.get('after')}")
        prompt_parts.append(f"- {f['table']}.{f['field']}: {', '.join(descs)}")

    prompt_parts.append("""
Please generate a concise summary (3-5 sentences) covering:
1. Overall scope of changes (small/medium/large)
2. The most important 3 changes
3. Whether there are any breaking / destructive changes
Return only the summary text, no extra formatting.""")

    from app.ai.client import ai_client, AIServiceError
    import asyncio

    try:
        summary = await asyncio.to_thread(
            ai_client.complete,
            "You are a database schema change analyst. Summarize the following diff concisely.",
            "\n".join(prompt_parts),
            max_tokens=1024,
            temperature=0.3,
        )
    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))

    await repo.update_diff_summary(diff_id, summary)
    await db.commit()

    return {"summary": summary}


# ── Migration export endpoint ────────────────────────────────────────


@router.post("/diff/{diff_id}/migration", response_class=PlainTextResponse)
async def diff_migration(project_id: str, diff_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    diff = await repo.get_diff(diff_id)
    if diff is None or diff.project_id != project_id:
        raise HTTPException(status_code=404, detail="Diff not found")

    project_info = await repo.get_project(project_id)
    dialect = project_info.get("dialect", "mysql") if project_info else "mysql"

    script = generate_alter_scripts(diff.diff_data, dialect)

    return PlainTextResponse(content=script, media_type="text/x-sql")
