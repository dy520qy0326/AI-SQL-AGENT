from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import RelationData, Repository


def _singularize(word: str) -> str:
    """Reverse English pluralization: users→user, categories→category, boxes→box."""
    w = word.lower()
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("sses") or w.endswith("shes") or w.endswith("ches") or w.endswith("xes") or w.endswith("zes"):
        return w[:-2]
    if w.endswith("ses") and len(w) > 3:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 1:
        return w[:-1]
    return w


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

        # Build a set of (source_table_id, tuple(columns)) covered by explicit FKs
        covered_pairs: set[tuple[str, tuple]] = set()

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
            covered_pairs.add((r.source_table_id, tuple(sorted(r.source_columns))))
            relations.append(r)

        # ── Step 2: _id suffix inference ──
        for table in tables:
            for col in table.columns:
                if not col.name.lower().endswith("_id"):
                    continue
                prefix = col.name[:-3]  # remove "_id"
                if not prefix:
                    continue
                prefix_lower = prefix.lower()

                # Check if already covered by an explicit FK on this exact column
                pair_key = (table.id, tuple(sorted([col.name])))
                if pair_key in covered_pairs:
                    continue

                # Exact table name match
                target = tables_dict.get(prefix_lower)
                if target and target.id != table.id:
                    relations.append(_make_inferred(
                        table, col, target, "id",
                        confidence=0.85,
                        source=f"naming convention: {col.name} → {target.name}.id",
                    ))
                    covered_pairs.add((table.id, tuple(sorted([col.name]))))
                    continue

                # Fuzzy: singularize each table name and match against prefix
                for tname, tgt in tables_dict.items():
                    if tgt.id == table.id:
                        continue
                    if _singularize(tname) == prefix_lower:
                        relations.append(_make_inferred(
                            table, col, tgt, "id",
                            confidence=0.70,
                            source=f"naming convention (singularized): {col.name} → {tgt.name}.id",
                        ))
                        covered_pairs.add((table.id, tuple(sorted([col.name]))))
                        break

        # ── Step 3: Same-name, same-type non-PK columns ──
        col_groups: dict[tuple[str, str], list[tuple]] = {}  # (name_lower, type) → [(table_id, col_name)]
        for table in tables:
            for col in table.columns:
                if col.is_primary_key:
                    continue
                key = (col.name.lower(), col.data_type.lower())
                col_groups.setdefault(key, []).append((table.id, col.name))

        for (col_name_lower, _), entries in col_groups.items():
            if len(entries) < 2:
                continue
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    src_tid, src_cname = entries[i]
                    tgt_tid, tgt_cname = entries[j]
                    if src_tid == tgt_tid:
                        continue
                    pair_key = (src_tid, tuple(sorted([src_cname])))
                    if pair_key in covered_pairs:
                        continue
                    src_table = next(t for t in tables if t.id == src_tid)
                    tgt_table = next(t for t in tables if t.id == tgt_tid)
                    relations.append(RelationData(
                        source_table_id=src_tid,
                        source_columns=[src_cname],
                        target_table_id=tgt_tid,
                        target_columns=[tgt_cname],
                        relation_type="INFERRED",
                        confidence=0.60,
                        source=f"same column name+type: {src_table.name}.{src_cname} ↔ {tgt_table.name}.{tgt_cname}",
                    ))
                    covered_pairs.add((src_tid, tuple(sorted([src_cname]))))

        # ── Step 4: N:M intermediate table detection ──
        nm_table_ids = set()
        for table in tables:
            fk_count = len([fk for fk in foreign_keys if fk.table_id == table.id])
            if len(table.columns) <= 5 and fk_count == 2:
                nm_table_ids.add(table.id)

        # Mark relations involving N:M tables
        for r in relations:
            if r.source_table_id in nm_table_ids or r.target_table_id in nm_table_ids:
                if r.source:
                    r.source += " [N:M intermediate]"

        # ── Step 5: Dedup (keep highest confidence) ──
        best: dict[tuple, RelationData] = {}
        for r in relations:
            key = _relation_key(r)
            if key not in best or r.confidence > best[key].confidence:
                best[key] = r

        return list(best.values())


def _make_inferred(table, col, target_table, target_col: str, confidence: float, source: str) -> RelationData:
    return RelationData(
        source_table_id=table.id,
        source_columns=[col.name],
        target_table_id=target_table.id,
        target_columns=[target_col],
        relation_type="INFERRED",
        confidence=confidence,
        source=source,
    )


async def detect_relations(project_id: str, db: AsyncSession) -> list[RelationData]:
    """Convenience function — run full detection for a project."""
    detector = RelationDetector(db)
    return await detector.detect(project_id)
