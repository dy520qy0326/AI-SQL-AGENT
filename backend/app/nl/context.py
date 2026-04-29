from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import Repository


@dataclass
class ContextPackage:
    system_prompt: str
    user_message: str
    candidate_tables: list[str] = field(default_factory=list)
    token_estimate: int = 0
    mode: str = "fuzzy"  # single / relation / search / fuzzy


async def build_context(
    db: AsyncSession,
    project_id: str,
    question: str,
    session_id: str | None = None,
) -> ContextPackage:
    """Analyze question and construct minimal-token schema context."""
    from app.ai.prompts import NL_QUERY_SYSTEM

    repo = Repository(db)
    tables = await repo.get_tables(project_id)
    relations = await repo.get_relations(project_id)

    if not tables:
        return ContextPackage(
            system_prompt=NL_QUERY_SYSTEM,
            user_message=question,
            token_estimate=50,
            mode="fuzzy",
        )

    question_lower = question.lower()

    # Collect all table names and column names
    table_names = [t.name.lower() for t in tables]
    table_by_name = {t.name.lower(): t for t in tables}

    # Match table names in question (longest first to avoid partial matches)
    matched_tables: list[str] = []
    for tname in sorted(table_names, key=len, reverse=True):
        if tname in question_lower and tname not in matched_tables:
            matched_tables.append(tname)

    # Match column names in question
    all_columns: dict[str, list[tuple[str, str]]] = {}  # col_name → [(table_name, col_name)]
    for t in tables:
        for c in t.columns:
            cl = c.name.lower()
            if cl not in all_columns:
                all_columns[cl] = []
            all_columns[cl].append((t.name, c.name))

    matched_columns: set[str] = set()
    for cname in sorted(all_columns.keys(), key=len, reverse=True):
        if cname in question_lower:
            matched_columns.add(cname)

    # Mode selection
    if len(matched_tables) == 0 and len(matched_columns) == 0:
        mode = "fuzzy"
    elif len(matched_tables) == 1 and len(matched_columns) == 0:
        mode = "single"
    elif 1 <= len(matched_tables) <= 3:
        mode = "relation"
    else:
        mode = "search"

    # Build schema text based on mode
    schema_text = _build_schema_text(
        mode, tables, relations, table_by_name, matched_tables, matched_columns, all_columns
    )

    # Inject conversation history if session exists
    history_text = ""
    if session_id:
        history_text = await _get_history_text(repo, session_id)

    # Build the NL_QUERY_SYSTEM with schema context
    full_system = NL_QUERY_SYSTEM + f"\n\n## DATABASE SCHEMA\n{schema_text}"

    user_message = question
    if history_text:
        user_message = f"Previous conversation:\n{history_text}\n\nCurrent question: {question}"

    # Rough token estimate (4 chars ≈ 1 token)
    token_estimate = len(full_system + user_message) // 4

    return ContextPackage(
        system_prompt=full_system,
        user_message=user_message,
        candidate_tables=matched_tables,
        token_estimate=token_estimate,
        mode=mode,
    )


def _build_schema_text(
    mode: str,
    tables: list,
    relations: list,
    table_by_name: dict,
    matched_tables: list[str],
    matched_columns: set[str],
    all_columns: dict,
) -> str:
    if mode == "fuzzy":
        return _summary_mode(tables, max_tables=30)
    elif mode == "single":
        t = table_by_name[matched_tables[0]]
        related_tables = _related_table_names(t, relations, tables)
        return _full_schema([t] + related_tables, relations, highlight_table=t.name)
    elif mode == "relation":
        target_tables = [table_by_name[n] for n in matched_tables if n in table_by_name]
        return _full_schema(target_tables, relations)
    else:  # search
        return _search_mode(tables, matched_columns, all_columns)


def _summary_mode(tables: list, max_tables: int = 30) -> str:
    lines = [f"Project has {len(tables)} tables (showing first {max_tables}):"]
    for t in tables[:max_tables]:
        pk = [c.name for c in t.columns if c.is_primary_key]
        fk = [c.name for c in t.columns if c.name.endswith("_id")]
        cols = pk + [c for c in fk if c not in pk]
        lines.append(f"  {t.name}: PK={pk}, key_cols={cols}")
    return "\n".join(lines)


def _full_schema(tables: list, relations: list, highlight_table: str | None = None) -> str:
    table_ids = {t.id for t in tables}
    lines = []

    for t in tables:
        marker = " ← CURRENT" if t.name == highlight_table else ""
        desc = f" ({t.comment})" if t.comment else ""
        lines.append(f"## Table: {t.name}{marker}{desc}")
        lines.append("| Column | Type | PK | FK | Nullable | Comment |")
        lines.append("|--------|------|----|----|----------|---------|")

        fk_cols = set()
        for f in t.foreign_keys:
            fk_cols.update(f.columns)

        for c in t.columns:
            pk = "✓" if c.is_primary_key else ""
            fk = "✓" if c.name in fk_cols else ""
            nl = "YES" if c.nullable else "NO"
            comment = c.comment or ""
            lines.append(f"| {c.name} | {c.data_type} | {pk} | {fk} | {nl} | {comment} |")
        lines.append("")

    # Add relations involving these tables
    relevant = [r for r in relations if r.source_table_id in table_ids or r.target_table_id in table_ids]
    if relevant:
        lines.append("## Relationships")
        id_to_name = {t.id: t.name for t in tables}
        for r in relevant:
            src = id_to_name.get(r.source_table_id, "?")
            tgt = id_to_name.get(r.target_table_id, "?")
            lines.append(
                f"  {src}.{','.join(r.source_columns)} → {tgt}.{','.join(r.target_columns)} "
                f"[{r.relation_type}, confidence={r.confidence}]"
            )

    return "\n".join(lines)


def _search_mode(tables: list, matched_columns: set[str], all_columns: dict) -> str:
    lines = ["## Tables and Columns Index"]
    for t in tables:
        cols = [c.name for c in t.columns]
        lines.append(f"  {t.name}: {', '.join(cols)}")

    if matched_columns:
        lines.append("\n## Matched Columns")
        for cname in matched_columns:
            locations = all_columns.get(cname, [])
            for tname, colname in locations:
                lines.append(f"  {tname}.{colname}")

    return "\n".join(lines)


def _related_table_names(table, relations: list, all_tables: list) -> list:
    """Find tables directly related to the given table."""
    related_ids: set[str] = set()
    for r in relations:
        if r.source_table_id == table.id:
            related_ids.add(r.target_table_id)
        elif r.target_table_id == table.id:
            related_ids.add(r.source_table_id)

    result = []
    for t in all_tables:
        if t.id in related_ids and t.id != table.id:
            result.append(t)
    return result


async def _get_history_text(repo: Repository, session_id: str) -> str:
    msgs = await repo.get_messages(session_id, limit=10)
    if not msgs:
        return ""
    lines = []
    for m in msgs:
        role = "User" if m.role == "user" else "Assistant"
        content = m.content[:200] if len(m.content) > 200 else m.content
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
