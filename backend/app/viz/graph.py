from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.graph import ColumnBrief, GraphEdge, GraphNode
from app.store.repository import Repository


async def build_graph(
    project_id: str,
    db: AsyncSession,
    min_confidence: float = 0.0,
    type_filter: str | None = None,
    table_ids: set[str] | None = None,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    repo = Repository(db)
    tables = await repo.get_tables(project_id)
    relations = await repo.get_relations(project_id, type_filter=type_filter, min_confidence=min_confidence)

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

    # Collect all FK column names per table for marking
    fk_columns: dict[str, set[str]] = {}  # table_id → set of column names
    for r in relations:
        fk_columns.setdefault(r.source_table_id, set()).update(r.source_columns)

    nodes = []
    for t in tables:
        cols = []
        for c in (t.columns or []):
            cols.append(ColumnBrief(
                name=c.name,
                type=c.data_type,
                pk=c.is_primary_key,
                fk=c.name in fk_columns.get(t.id, set()),
            ))
        nodes.append(GraphNode(
            id=t.id,
            label=t.name,
            schema_name=t.schema_name or "",
            column_count=len(cols),
            columns=cols,
        ))

    tmap = {t.id: t.name for t in tables}
    edges = []
    for r in relations:
        src_name = tmap.get(r.source_table_id, "?")
        tgt_name = tmap.get(r.target_table_id, "?")
        label = f"{','.join(r.source_columns)} → {','.join(r.target_columns)}"
        edges.append(GraphEdge(
            id=r.id,
            from_=r.source_table_id,
            to=r.target_table_id,
            label=label,
            type=r.relation_type,
            confidence=r.confidence,
            dashes=r.relation_type != "FOREIGN_KEY",
        ))

    return nodes, edges
