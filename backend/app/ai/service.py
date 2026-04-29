import hashlib
import json
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import get_cached, make_cache_key, set_cache
from app.ai.client import AIServiceError, ai_client
from app.ai.prompts import (
    COMMENT_COMPLETION_SYSTEM,
    COMMENT_COMPLETION_USER,
    PROJECT_SUMMARY_SYSTEM,
    PROJECT_SUMMARY_USER,
    RELATION_COMPLETION_SYSTEM,
    RELATION_COMPLETION_USER,
    TABLE_DESCRIPTION_SYSTEM,
    TABLE_DESCRIPTION_USER,
)
from app.store.repository import RelationData, Repository

logger = logging.getLogger(__name__)

# Per-project locks for AI concurrency control
_locks: dict[str, "asyncio.Lock"] = {}


def _get_lock(project_id: str) -> "asyncio.Lock":
    import asyncio

    if project_id not in _locks:
        _locks[project_id] = asyncio.Lock()
    return _locks[project_id]


def compute_schema_hash(tables: list) -> str:
    """Stable hash of table+column names for cache keying."""
    parts = []
    for t in sorted(tables, key=lambda x: x.name):
        cols = sorted([c.name for c in t.columns])
        parts.append(f"{t.name}:{','.join(cols)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def compute_prompt_hash(prompt_template: str) -> str:
    return hashlib.sha256(prompt_template.encode()).hexdigest()


def _parse_ai_json(text: str) -> dict:
    """Extract JSON from AI response, handling markdown fences."""
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    return json.loads(text)


async def complete_relations(project_id: str, db: AsyncSession) -> dict:
    """AI-powered relation completion for previously unlinked tables."""
    repo = Repository(db)

    # 1. Find isolated tables (those without any Relation)
    all_tables = await repo.get_tables(project_id)
    all_relations = await repo.get_relations(project_id)

    linked_ids: set[str] = set()
    for r in all_relations:
        linked_ids.add(r.source_table_id)
        linked_ids.add(r.target_table_id)

    isolated = [t for t in all_tables if t.id not in linked_ids]
    if len(isolated) <= 1:
        return {"new_relations": 0, "message": "no isolated tables to analyze", "cache_hit": False}

    # 2. Build token-compressed JSON (table name + PK + _id columns only)
    unlinked_json = []
    for t in isolated:
        pk_cols = [c.name for c in t.columns if c.is_primary_key]
        fk_like = [c.name for c in t.columns if c.name.endswith("_id")]
        unlinked_json.append({
            "table": t.name,
            "primary_keys": pk_cols,
            "key_columns": list(set(pk_cols + fk_like)),
        })

    # Known tables (have relations)
    known = [t for t in all_tables if t.id in linked_ids]
    known_json: list[str] = [t.name for t in known]

    # Existing relations summary
    existing_json = []
    for r in all_relations:
        src_t = next((t for t in all_tables if t.id == r.source_table_id), None)
        tgt_t = next((t for t in all_tables if t.id == r.target_table_id), None)
        if src_t and tgt_t:
            existing_json.append({
                "source_table": src_t.name,
                "source_columns": r.source_columns,
                "target_table": tgt_t.name,
                "target_columns": r.target_columns,
                "type": r.relation_type,
            })

    # 3. Check cache
    schema_hash = compute_schema_hash(all_tables)
    prompt_hash = compute_prompt_hash(RELATION_COMPLETION_USER)
    cache_key = make_cache_key(schema_hash, prompt_hash)
    cached = await get_cached(db, cache_key)

    if cached is not None:
        relations = _apply_relation_results(cached.get("relations", []), all_tables)
        await repo.save_relations(project_id, relations)
        return {
            "new_relations": len(relations),
            "relations": [_relation_to_dict(r, all_tables) for r in relations],
            "cache_hit": True,
            "message": f"restored {len(relations)} AI-suggested relations from cache",
        }

    # 4. Call AI
    user_message = RELATION_COMPLETION_USER.format(
        known_tables_json=json.dumps(known_json, ensure_ascii=False),
        unlinked_tables_json=json.dumps(unlinked_json, ensure_ascii=False),
        existing_relations_json=json.dumps(existing_json, ensure_ascii=False),
    )

    try:
        response_text = await _run_async(ai_client.complete, RELATION_COMPLETION_SYSTEM, user_message)
        ai_result = _parse_ai_json(response_text)
    except (AIServiceError, json.JSONDecodeError) as e:
        logger.error("Relation completion failed: %s", e)
        raise

    raw_relations = ai_result.get("relations", [])

    # 5. Filter and validate
    valid_relations: list[RelationData] = []
    low_count = 0
    invalid_count = 0

    table_name_to_id = {t.name.lower(): t.id for t in all_tables}

    for item in raw_relations:
        confidence_str = item.get("confidence", "LOW").upper()
        if confidence_str == "LOW":
            low_count += 1
            continue

        src_name = item.get("source_table", "").lower()
        tgt_name = item.get("target_table", "").lower()
        if src_name not in table_name_to_id or tgt_name not in table_name_to_id:
            invalid_count += 1
            continue

        confidence = 0.85 if confidence_str == "HIGH" else 0.65
        valid_relations.append(RelationData(
            source_table_id=table_name_to_id[src_name],
            source_columns=[item.get("source_column", "id")],
            target_table_id=table_name_to_id[tgt_name],
            target_columns=[item.get("target_column", "id")],
            relation_type="INFERRED",
            confidence=confidence,
            source=f"AI suggested: {item.get('reason', 'no reason given')}",
        ))

    logger.info(
        "AI relation completion: %d valid, %d LOW filtered, %d invalid, %d tables analyzed",
        len(valid_relations), low_count, invalid_count, len(isolated),
    )

    # 6. Save and cache
    await repo.save_relations(project_id, valid_relations)
    await set_cache(db, cache_key, prompt_hash, schema_hash, {"relations": raw_relations})

    return {
        "new_relations": len(valid_relations),
        "relations": [_relation_to_dict(r, all_tables) for r in valid_relations],
        "cache_hit": False,
        "message": f"AI suggested {len(valid_relations)} relations ({low_count} LOW filtered)",
    }


async def complete_comments(project_id: str, db: AsyncSession) -> dict:
    """AI-powered comment completion for columns without descriptions."""
    repo = Repository(db)

    # 1. Gather columns missing comments
    tables = await repo.get_tables(project_id)
    missing: list[dict] = []
    for t in tables:
        for c in t.columns:
            if not c.comment:
                missing.append({"table": t.name, "column": c.name, "type": c.data_type})

    if not missing:
        return {"updated": 0, "fields": [], "message": "no missing comments", "cache_hit": False}

    # 2. Check cache
    schema_hash = compute_schema_hash(tables)
    prompt_hash = compute_prompt_hash(COMMENT_COMPLETION_USER)
    cache_key = make_cache_key(schema_hash, prompt_hash)
    cached = await get_cached(db, cache_key)

    if cached is not None:
        suggestions = cached.get("suggestions", [])
        updated = await _apply_comment_suggestions(repo, tables, suggestions)
        return {"updated": updated, "fields": suggestions, "cache_hit": True, "message": f"restored {updated} comments from cache"}

    # 3. Call AI
    # Token budget: ~20 cols per batch
    batch = missing[:30]
    context = f"Project has {len(tables)} tables. Filling missing column comments."
    columns_json = json.dumps(batch, ensure_ascii=False)
    user_message = COMMENT_COMPLETION_USER.format(project_context=context, columns_json=columns_json)

    try:
        response_text = await _run_async(ai_client.complete, COMMENT_COMPLETION_SYSTEM, user_message, 2048)
        ai_result = _parse_ai_json(response_text)
    except (AIServiceError, json.JSONDecodeError) as e:
        logger.error("Comment completion failed: %s", e)
        raise

    suggestions = ai_result.get("suggestions", [])

    # 4. Apply suggestions
    updated = await _apply_comment_suggestions(repo, tables, suggestions)
    await set_cache(db, cache_key, prompt_hash, schema_hash, {"suggestions": suggestions})

    return {"updated": updated, "fields": suggestions, "cache_hit": False, "message": f"AI generated {updated} comments"}


async def generate_table_descriptions(project_id: str, db: AsyncSession) -> dict:
    """AI-generated table descriptions for tables without comments."""
    repo = Repository(db)
    tables = await repo.get_tables(project_id)
    missing = [t for t in tables if not t.comment]
    if not missing:
        return {"updated": 0, "descriptions": [], "message": "no tables need descriptions"}

    summary = []
    for t in tables:
        cols = [f"{c.name} {c.data_type}" + (" PK" if c.is_primary_key else "") for c in t.columns[:10]]
        summary.append(f"{t.name}: {', '.join(cols)}")

    user_message = TABLE_DESCRIPTION_USER.format(all_tables_summary="\n".join(summary))

    try:
        response_text = await _run_async(ai_client.complete, TABLE_DESCRIPTION_SYSTEM, user_message, 2048)
        ai_result = _parse_ai_json(response_text)
    except (AIServiceError, json.JSONDecodeError) as e:
        logger.error("Table description failed: %s", e)
        raise

    descriptions = ai_result.get("descriptions", [])
    table_name_map = {t.name.lower(): t for t in tables}

    from sqlalchemy import update

    from app.db.models import Table

    updated = 0
    for item in descriptions:
        tname = item.get("table", "").lower()
        desc = item.get("description", "")
        if tname in table_name_map and desc:
            await db.execute(
                update(Table).where(Table.id == table_name_map[tname].id).values(comment=desc + " [AI Generated]")
            )
            updated += 1

    await db.flush()
    return {"updated": updated, "descriptions": descriptions, "message": f"AI described {updated} tables"}


async def generate_project_summary(project_id: str, db: AsyncSession) -> str:
    """AI-generated overall project data model summary."""
    repo = Repository(db)
    tables = await repo.get_tables(project_id)
    relations = await repo.get_relations(project_id)

    lines = []
    for t in tables:
        pk = [c.name for c in t.columns if c.is_primary_key]
        lines.append(f"  {t.name}: PK={pk}, {len(t.columns)} columns")
    schema_text = "\n".join(lines)

    rel_text = "\n".join(
        f"  {r.relation_type}: {r.source_columns} → {r.target_columns} (confidence={r.confidence})"
        for r in relations[:20]
    )

    user_message = PROJECT_SUMMARY_USER.format(
        table_count=len(tables),
        relation_count=len(relations),
        schema_summary=f"Tables:\n{schema_text}\n\nRelations:\n{rel_text}",
    )

    try:
        response_text = await _run_async(ai_client.complete, PROJECT_SUMMARY_SYSTEM, user_message, 2048)
        ai_result = _parse_ai_json(response_text)
    except (AIServiceError, json.JSONDecodeError) as e:
        logger.error("Project summary failed: %s", e)
        raise

    return ai_result.get("summary", "")


async def _run_async(func, *args, **kwargs):
    """Run a sync function in a thread pool."""
    import asyncio
    return await asyncio.to_thread(func, *args, **kwargs)


def _relation_to_dict(r: RelationData, tables: list) -> dict:
    src_t = next((t for t in tables if t.id == r.source_table_id), None)
    tgt_t = next((t for t in tables if t.id == r.target_table_id), None)
    return {
        "source_table": src_t.name if src_t else "?",
        "source_columns": r.source_columns,
        "target_table": tgt_t.name if tgt_t else "?",
        "target_columns": r.target_columns,
        "relation_type": r.relation_type,
        "confidence": r.confidence,
        "source": r.source,
    }


def _apply_relation_results(raw_relations: list, tables: list) -> list[RelationData]:
    """Parse cached AI relation result into RelationData list."""
    result: list[RelationData] = []
    table_name_to_id = {t.name.lower(): t.id for t in tables}

    for item in raw_relations:
        confidence_str = item.get("confidence", "LOW").upper()
        if confidence_str == "LOW":
            continue

        src_name = item.get("source_table", "").lower()
        tgt_name = item.get("target_table", "").lower()
        if src_name not in table_name_to_id or tgt_name not in table_name_to_id:
            continue

        confidence = 0.85 if confidence_str == "HIGH" else 0.65
        result.append(RelationData(
            source_table_id=table_name_to_id[src_name],
            source_columns=[item.get("source_column", "id")],
            target_table_id=table_name_to_id[tgt_name],
            target_columns=[item.get("target_column", "id")],
            relation_type="INFERRED",
            confidence=confidence,
            source=f"AI suggested: {item.get('reason', 'no reason given')}",
        ))

    return result


async def _apply_comment_suggestions(repo: Repository, tables: list, suggestions: list) -> int:
    from sqlalchemy import update

    from app.db.models import Column

    updated = 0
    table_col_map: dict[tuple[str, str], str] = {}
    for t in tables:
        for c in t.columns:
            table_col_map[(t.name.lower(), c.name.lower())] = c.id

    for item in suggestions:
        tname = item.get("table", "").lower()
        cname = item.get("column", "").lower()
        comment = item.get("comment", "")
        key = (tname, cname)
        if key in table_col_map and comment:
            new_comment = comment + " [AI Generated]"
            await repo.db.execute(
                update(Column).where(Column.id == table_col_map[key]).values(comment=new_comment)
            )
            updated += 1

    await repo.db.flush()
    return updated
