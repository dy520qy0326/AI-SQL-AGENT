from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import RelationData, Repository


def _relation_key(r: RelationData) -> tuple:
    """De-duplication key for a relation."""
    return (
        r.source_table_id,
        tuple(sorted(r.source_columns)),
        r.target_table_id,
        tuple(sorted(r.target_columns)),
    )


class RelationDetector:
    def __init__(self, db: AsyncSession):
        self.repo = Repository(db)

    async def detect(self, project_id: str) -> list[RelationData]:
        tables = await self.repo.get_tables(project_id)
        if not tables:
            return []

        tables_dict = {t.name.lower(): t for t in tables}
        foreign_keys = await self.repo.get_project_foreign_keys(project_id)

        relations: list[RelationData] = []

        # ── Step 1: Explicit foreign keys ──
        for fk in foreign_keys:
            ref_name = fk.ref_table_name.lower()
            target = tables_dict.get(ref_name)
            if target is None:
                continue
            r = RelationData(
                source_table_id=fk.table_id,
                source_columns=list(fk.columns),
                target_table_id=target.id,
                target_columns=list(fk.ref_columns),
                relation_type="FOREIGN_KEY",
                confidence=1.0,
                source=f"DDL explicit FK: {fk.constraint_name or 'unnamed'}",
            )
            relations.append(r)

        # ── Dedup (keep highest confidence) ──
        best: dict[tuple, RelationData] = {}
        for r in relations:
            key = _relation_key(r)
            if key not in best or r.confidence > best[key].confidence:
                best[key] = r

        return list(best.values())


async def detect_relations(project_id: str, db: AsyncSession) -> list[RelationData]:
    """Convenience function — run full detection for a project."""
    detector = RelationDetector(db)
    return await detector.detect(project_id)
