from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import Repository

MERMAID_TEMPLATE = """erDiagram
{entities}
{relationships}
"""

# Mermaid erDiagram treats "PK" and "FK" (any case) as keyword tokens.
# Column names that match these keywords cause parse errors.
_KEYWORDS = frozenset({"pk", "fk"})

# Limit columns shown per table in ER diagram to prevent one wide table
# from dominating the layout when there are few tables in the view.
MAX_COLS_PER_TABLE = 15


async def build_mermaid(
    project_id: str,
    db: AsyncSession,
    min_confidence: float = 0.0,
    table_ids: set[str] | None = None,
) -> str:
    repo = Repository(db)
    tables = await repo.get_tables(project_id)
    relations = await repo.get_relations(project_id, min_confidence=min_confidence)

    # 1-hop expansion: if table_ids specified, include neighbor tables
    if table_ids is not None:
        neighbor_ids = set()
        for r in relations:
            if r.source_table_id in table_ids:
                neighbor_ids.add(r.target_table_id)
            if r.target_table_id in table_ids:
                neighbor_ids.add(r.source_table_id)
        expanded = table_ids | neighbor_ids
        tables = [t for t in tables if t.id in expanded]
        relations = [r for r in relations if r.source_table_id in expanded and r.target_table_id in expanded]

    tmap = {t.id: t for t in tables}

    # Collect FK columns
    fk_cols: dict[str, set[str]] = {}
    for r in relations:
        fk_cols.setdefault(r.source_table_id, set()).update(r.source_columns)

    # Build entities
    entity_lines = []
    for t in tables:
        cols = t.columns or []
        shown = cols[:MAX_COLS_PER_TABLE]
        hidden = len(cols) - len(shown)
        display = t.name if hidden == 0 else f"{t.name} ({len(cols)} cols, {hidden} hidden)"
        lines = [f'  {_mermaid_id(t.id)}["{display}"] {{']
        for c in shown:
            suffix = ""
            if c.is_primary_key:
                suffix = " PK"
            elif c.name in fk_cols.get(t.id, set()):
                suffix = " FK"
            lines.append(f'    {c.data_type} {_safe_col(c.name)}{suffix}')
        lines.append("  }")
        entity_lines.append("\n".join(lines))

    # Build relationships
    rel_lines = []
    for r in relations:
        src = _mermaid_id(r.source_table_id)
        tgt = _mermaid_id(r.target_table_id)
        src_name = tmap.get(r.source_table_id)
        tgt_name = tmap.get(r.target_table_id)
        src_label = src_name.name if src_name else "?"
        tgt_label = tgt_name.name if tgt_name else "?"

        # Choose relationship style
        if r.source_table_id == r.target_table_id:
            arrow = "}o--o{"
        else:
            arrow = "||--o{"

        label = f'{",".join(r.source_columns)} → {",".join(r.target_columns)}'
        if r.relation_type == "INFERRED":
            label += f" [inferred, {r.confidence}]"
        else:
            label += f" [FK]"

        rel_lines.append(f"  {src} {arrow} {tgt} : \"{label}\"")

    return MERMAID_TEMPLATE.format(
        entities="\n".join(entity_lines),
        relationships="\n".join(rel_lines),
    )


def _mermaid_id(table_id: str) -> str:
    """Generate a safe Mermaid identifier from a UUID."""
    return "t_" + table_id.replace("-", "_")


def _safe_col(name: str) -> str:
    """Escape column names that conflict with Mermaid erDiagram keywords.

    Mermaid's erDiagram tokenizer treats 'pk'/'fk' (any case) as
    ATTRIBUTE_KEY tokens instead of ATTRIBUTE_WORD, causing parse errors.
    Appending an underscore avoids the keyword match with minimal visual
    impact.
    """
    if name.lower() in _KEYWORDS:
        return name + "_"
    return name
