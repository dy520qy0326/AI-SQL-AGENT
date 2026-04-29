import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    tables_added: list[dict] = field(default_factory=list)
    tables_removed: list[dict] = field(default_factory=list)
    tables_renamed: list[dict] = field(default_factory=list)
    fields_added: list[dict] = field(default_factory=list)
    fields_removed: list[dict] = field(default_factory=list)
    fields_modified: list[dict] = field(default_factory=list)
    fields_renamed: list[dict] = field(default_factory=list)
    indexes_added: list[dict] = field(default_factory=list)
    indexes_removed: list[dict] = field(default_factory=list)
    relations_added: list[dict] = field(default_factory=list)
    relations_removed: list[dict] = field(default_factory=list)
    breaking_changes: bool = False
    breaking_details: list[str] = field(default_factory=list)
    summary_stats: dict = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _field_signature(col: dict) -> str:
    """Normalized field signature for rename detection."""
    return f"{col.get('type', '')}|{col.get('length', '')}|{col.get('nullable', True)}"


def _get_table_key(table: dict) -> str:
    """Normalized table name for lookup."""
    return (table.get("schema_", "") + "." + table["name"]).lower()


def _build_table_index(tables: list[dict]) -> dict[str, dict]:
    return {_get_table_key(t): t for t in tables}


# ── Breaking change detection ────────────────────────────────────────

_TYPE_PRIORITY = {"bigint": 5, "int": 4, "smallint": 3, "tinyint": 2}


def _is_type_narrowing(old_type: str, new_type: str) -> bool:
    ot = old_type.lower().split("(")[0].strip()
    nt = new_type.lower().split("(")[0].strip()
    if ot in _TYPE_PRIORITY and nt in _TYPE_PRIORITY:
        return _TYPE_PRIORITY[nt] < _TYPE_PRIORITY[ot]
    return False


def _is_length_shortening(old_len: Any, new_len: Any) -> bool:
    try:
        return int(new_len) < int(old_len)
    except (TypeError, ValueError):
        return False


def _check_field_breaking(before: dict, after: dict, table: str, field: str, details: list) -> None:
    # Type narrowing
    if _is_type_narrowing(before.get("type", ""), after.get("type", "")):
        details.append(f"{table}.{field}: type narrowed {before['type']} → {after['type']}")

    # NOT NULL → NULL
    if before.get("nullable") is False and after.get("nullable") is True:
        details.append(f"{table}.{field}: NOT NULL → NULL")

    # Length shortening
    old_len = before.get("length")
    new_len = after.get("length")
    if _is_length_shortening(old_len, new_len):
        details.append(f"{table}.{field}: length shortened {old_len} → {new_len}")


# ── Table matching ───────────────────────────────────────────────────


def _match_tables(old_tables: list[dict], new_tables: list[dict]) -> tuple[list[dict], list[dict], list[dict], dict[str, str]]:
    """Match tables between old and new versions.

    Returns:
        (tables_added, tables_removed, tables_renamed, name_map)
        name_map: old_name_lower → new_name_lower for renamed tables
    """
    old_index = _build_table_index(old_tables)
    new_index = _build_table_index(new_tables)

    added: list[dict] = []
    removed: list[dict] = []
    renamed: list[dict] = []
    name_map: dict[str, str] = {}

    # Find exact matches
    matched_old: set[str] = set()
    matched_new: set[str] = set()

    for okey, ot in old_index.items():
        if okey in new_index:
            matched_old.add(okey)
            matched_new.add(okey)
            name_map[okey] = okey

    # Try rename detection for unmatched tables
    unmatched_old = {k: v for k, v in old_index.items() if k not in matched_old}
    unmatched_new = {k: v for k, v in new_index.items() if k not in matched_new}

    for okey, ot in unmatched_old.items():
        old_name = ot["name"]
        old_fields = {c["name"] for c in ot.get("columns", [])}
        best_match = None
        best_score = 0.0

        for nkey, nt in unmatched_new.items():
            new_name = nt["name"]
            new_fields = {c["name"] for c in nt.get("columns", [])}
            edit_dist = _levenshtein(old_name.lower(), new_name.lower())
            field_sim = _jaccard_similarity(old_fields, new_fields)
            field_overlap = len(old_fields & new_fields) / max(len(old_fields), 1) if old_fields else 0

            # Score: edit distance (closer = better) + field similarity
            edit_score = max(0, 1 - edit_dist / max(len(old_name), len(new_name), 1))
            score = edit_score * 0.4 + field_sim * 0.3 + field_overlap * 0.3

            if score > best_score and score >= 0.55:
                best_score = score
                best_match = nkey

        if best_match:
            renamed.append({
                "old_name": ot["name"],
                "new_name": unmatched_new[best_match]["name"],
                "similarity": round(best_score, 3),
            })
            name_map[okey] = best_match
            matched_old.add(okey)
            matched_new.add(best_match)

    # Remaining unmatched = added / removed
    for okey, ot in old_index.items():
        if okey not in matched_old:
            removed.append(ot)

    for nkey, nt in new_index.items():
        if nkey not in matched_new:
            added.append(nt)

    return added, removed, renamed, name_map


# ── Field comparison ─────────────────────────────────────────────────


def _compare_fields(old_table: dict, new_table: dict, breaking_details: list) -> list[dict]:
    """Compare fields between two matched tables. Returns fields_modified list."""
    table_name = old_table["name"]
    modified: list[dict] = []
    old_cols = {c["name"].lower(): c for c in old_table.get("columns", [])}
    new_cols = {c["name"].lower(): c for c in new_table.get("columns", [])}

    for name in old_cols:
        if name in new_cols:
            oc = old_cols[name]
            nc = new_cols[name]
            changes = {}
            if oc.get("type") != nc.get("type"):
                changes["type"] = {"before": oc.get("type"), "after": nc.get("type")}
            if oc.get("length") != nc.get("length"):
                changes["length"] = {"before": oc.get("length"), "after": nc.get("length")}
            if oc.get("nullable") != nc.get("nullable"):
                changes["nullable"] = {"before": oc.get("nullable"), "after": nc.get("nullable")}
            if oc.get("default") != nc.get("default"):
                changes["default"] = {"before": oc.get("default"), "after": nc.get("default")}

            if changes:
                before = {"type": oc.get("type"), "length": oc.get("length"), "nullable": oc.get("nullable"), "default": oc.get("default")}
                after = {"type": nc.get("type"), "length": nc.get("length"), "nullable": nc.get("nullable"), "default": nc.get("default")}
                modified.append({
                    "table": table_name,
                    "field": oc["name"],
                    "changes": changes,
                    "before": before,
                    "after": after,
                })
                _check_field_breaking(before, after, table_name, oc["name"], breaking_details)

    return modified


def _find_field_changes(old_table: dict, new_table: dict, breaking_details: list) -> dict:
    """Find added, removed, modified, and renamed fields between two matched tables."""
    table_name = old_table["name"]
    old_cols = {c["name"].lower(): c for c in old_table.get("columns", [])}
    new_cols = {c["name"].lower(): c for c in new_table.get("columns", [])}

    old_names = set(old_cols.keys())
    new_names = set(new_cols.keys())

    # Exact match: same name → compare
    modified = _compare_fields(old_table, new_table, breaking_details)

    # Added: in new but not in old
    added_names = new_names - old_names
    fields_added = [
        {"table": table_name, "field": new_cols[n]["name"], "definition": new_cols[n]}
        for n in added_names
    ]

    # Removed: in old but not in new
    removed_names = old_names - new_names
    fields_removed = [
        {"table": table_name, "field": old_cols[n]["name"], "definition": old_cols[n]}
        for n in removed_names
    ]

    # Rename detection: match removed+added pairs by position + type
    fields_renamed = []
    if removed_names and added_names:
        removed_list = sorted(removed_names, key=lambda n: old_cols[n].get("ordinal_position", 0))
        added_list = sorted(added_names, key=lambda n: new_cols[n].get("ordinal_position", 0))
        used_added = set()

        for rn in removed_list:
            rc = old_cols[rn]
            best_match = None
            best_score = 0.0
            for an in added_list:
                if an in used_added:
                    continue
                ac = new_cols[an]
                edit_dist = _levenshtein(rc["name"].lower(), ac["name"].lower())
                sig_match = 1 if _field_signature(rc) == _field_signature(ac) else 0
                score = max(0, 1 - edit_dist / max(len(rc["name"]), 1)) * 0.5 + sig_match * 0.5
                if score > best_score and score >= 0.6:
                    best_score = score
                    best_match = an
            if best_match:
                fields_renamed.append({
                    "table": table_name,
                    "old_name": rc["name"],
                    "new_name": new_cols[best_match]["name"],
                    "similarity": round(best_score, 3),
                })
                used_added.add(best_match)

        # Remove renamed from added/removed lists
        fields_added = [f for f in fields_added if f["field"].lower() not in used_added]
        for rn in [r["old_name"].lower() for r in fields_renamed]:
            fields_removed = [f for f in fields_removed if f["field"].lower() != rn]

    # Breaking: removed fields
    for f in fields_removed:
        breaking_details.append(f"{table_name}.{f['field']}: field removed")

    return {
        "added": fields_added,
        "removed": fields_removed,
        "modified": modified,
        "renamed": fields_renamed,
    }


# ── Index comparison ─────────────────────────────────────────────────


def _compare_indexes(old_table: dict, new_table: dict, table_name: str) -> dict:
    old_idx = {i["name"].lower() for i in old_table.get("indexes", []) if i.get("name")}
    new_idx = {i["name"].lower() for i in new_table.get("indexes", []) if i.get("name")}

    added_names = new_idx - old_idx
    removed_names = old_idx - new_idx

    return {
        "added": [
            {"table": table_name, "index": i}
            for i in new_table.get("indexes", [])
            if i.get("name", "").lower() in added_names
        ],
        "removed": [
            {"table": table_name, "index": i}
            for i in old_table.get("indexes", [])
            if i.get("name", "").lower() in removed_names
        ],
    }


# ── Relation comparison ──────────────────────────────────────────────


def _compare_relations(old_table: dict, new_table: dict, table_name: str) -> dict:
    def rel_key(fk: dict) -> tuple:
        cols = tuple(fk.get("columns", []))
        ref = fk.get("ref_table", "")
        ref_cols = tuple(fk.get("ref_columns", []))
        return (cols, ref, ref_cols)

    old_keys = {rel_key(fk) for fk in old_table.get("foreign_keys", [])}
    new_keys = {rel_key(fk) for fk in new_table.get("foreign_keys", [])}

    added_keys = new_keys - old_keys
    removed_keys = old_keys - new_keys

    def find_by_key(fks: list[dict], key: tuple) -> dict | None:
        for fk in fks:
            if rel_key(fk) == key:
                return fk
        return None

    return {
        "added": [
            {"table": table_name, "relation": find_by_key(new_table.get("foreign_keys", []), k)}
            for k in added_keys
        ],
        "removed": [
            {"table": table_name, "relation": find_by_key(old_table.get("foreign_keys", []), k)}
            for k in removed_keys
        ],
    }


# ── Main entry point ─────────────────────────────────────────────────


def compute_diff(old_tables: list[dict], new_tables: list[dict]) -> DiffResult:
    """Compute structured schema diff between two versions of table lists.

    Args:
        old_tables: List of table dicts from the older version's parse_result.
        new_tables: List of table dicts from the newer version's parse_result.

    Returns:
        DiffResult containing all detected changes.
    """
    breaking_details: list[str] = []

    # Table-level matching
    tables_added, tables_removed, tables_renamed, name_map = _match_tables(old_tables, new_tables)

    # Build lookup maps
    old_index = _build_table_index(old_tables)
    new_index = _build_table_index(new_tables)

    # Field, index, and relation comparison for matched tables
    fields_added: list[dict] = []
    fields_removed: list[dict] = []
    fields_modified: list[dict] = []
    fields_renamed: list[dict] = []
    indexes_added: list[dict] = []
    indexes_removed: list[dict] = []
    relations_added: list[dict] = []
    relations_removed: list[dict] = []

    for okey, ot in old_index.items():
        nkey = name_map.get(okey)
        if nkey is None or nkey not in new_index:
            continue  # table was removed, already handled
        nt = new_index[nkey]
        table_name = ot["name"]

        # Fields
        fc = _find_field_changes(ot, nt, breaking_details)
        fields_added.extend(fc["added"])
        fields_removed.extend(fc["removed"])
        fields_modified.extend(fc["modified"])
        fields_renamed.extend(fc["renamed"])

        # Indexes
        ic = _compare_indexes(ot, nt, table_name)
        indexes_added.extend(ic["added"])
        indexes_removed.extend(ic["removed"])
        for idx in indexes_removed:
            breaking_details.append(f"{table_name}: index '{idx['index'].get('name', '?')}' removed")

        # Relations
        rc = _compare_relations(ot, nt, table_name)
        relations_added.extend(rc["added"])
        relations_removed.extend(rc["removed"])
        for rel in relations_removed:
            r = rel.get("relation", {})
            breaking_details.append(f"{table_name}: FK {r.get('columns', [])} → {r.get('ref_table', '?')} removed")

    # Breaking: table removed
    for t in tables_removed:
        breaking_details.append(f"table '{t['name']}' removed")

    breaking = len(breaking_details) > 0

    # Summary stats
    summary_stats = {
        "tables": {"added": len(tables_added), "removed": len(tables_removed), "renamed": len(tables_renamed)},
        "fields": {"added": len(fields_added), "removed": len(fields_removed), "modified": len(fields_modified), "renamed": len(fields_renamed)},
        "indexes": {"added": len(indexes_added), "removed": len(indexes_removed)},
        "relations": {"added": len(relations_added), "removed": len(relations_removed)},
        "breaking_count": len(breaking_details),
    }

    return DiffResult(
        tables_added=tables_added,
        tables_removed=tables_removed,
        tables_renamed=tables_renamed,
        fields_added=fields_added,
        fields_removed=fields_removed,
        fields_modified=fields_modified,
        fields_renamed=fields_renamed,
        indexes_added=indexes_added,
        indexes_removed=indexes_removed,
        relations_added=relations_added,
        relations_removed=relations_removed,
        breaking_changes=breaking,
        breaking_details=breaking_details,
        summary_stats=summary_stats,
    )
