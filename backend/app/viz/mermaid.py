from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import Repository

MERMAID_TEMPLATE = """erDiagram
{entities}
{relationships}
"""


async def build_mermaid(
    project_id: str,
    db: AsyncSession,
    min_confidence: float = 0.0,
) -> str:
    repo = Repository(db)
    tables = await repo.get_tables(project_id)
    relations = await repo.get_relations(project_id, min_confidence=min_confidence)

    tmap = {t.id: t for t in tables}

    # Collect FK columns
    fk_cols: dict[str, set[str]] = {}
    for r in relations:
        fk_cols.setdefault(r.source_table_id, set()).update(r.source_columns)

    # Build entities
    entity_lines = []
    for t in tables:
        lines = [f'  {_mermaid_id(t.id)}["{t.name}"] {{']
        for c in (t.columns or []):
            suffix = ""
            if c.is_primary_key:
                suffix = " PK"
            elif c.name in fk_cols.get(t.id, set()):
                suffix = " FK"
            lines.append(f'    {c.data_type} {c.name}{suffix}')
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
