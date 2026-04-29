from dataclasses import dataclass, field
import hashlib

import sqlglot
from sqlglot import exp


@dataclass
class DiscoveredRelation:
    temp_id: str
    source_table: str
    source_columns: list[str]
    target_table: str
    target_columns: list[str]
    join_type: str
    confidence: float = 1.0


def _make_temp_id(source_table: str, target_table: str, source_cols: list[str], target_cols: list[str]) -> str:
    """Deterministic temp ID based on relation content."""
    raw = "|".join([source_table, target_table] + sorted(source_cols) + sorted(target_cols))
    return hashlib.md5(raw.encode()).hexdigest()[:8]


_JOIN_TYPES: dict[str, str] = {
    "LEFT": "LEFT JOIN",
    "RIGHT": "RIGHT JOIN",
    "FULL": "FULL OUTER JOIN",
    "CROSS": "CROSS JOIN",
    "INNER": "INNER JOIN",
}


def _join_type_string(join: exp.Join) -> str:
    """Determine the join type string from a Join node."""
    side = join.args.get("side")
    kind = join.kind
    if side:
        return _JOIN_TYPES.get(side, f"{side} JOIN")
    if kind:
        return _JOIN_TYPES.get(kind, f"{kind} JOIN")
    return "INNER JOIN"


def _extract_aliases(tree: exp.Select) -> dict[str, str]:
    """Build a mapping of alias → real table name from FROM and JOIN clauses."""
    aliases: dict[str, str] = {}

    # FROM clause
    for from_node in tree.find_all(exp.From):
        tbl = from_node.this
        if isinstance(tbl, exp.Subquery):
            continue
        alias = tbl.alias or tbl.this.sql()
        name = tbl.this.sql()  # the actual table name
        aliases[alias.lower()] = name

    return aliases


def _is_subquery(node) -> bool:
    """Check if a table reference in a JOIN is a subquery."""
    return isinstance(node, exp.Subquery)


def _extract_on_conditions(
    on_expr: exp.Expr | None,
    aliases: dict[str, str],
) -> list[tuple[str | None, str, str | None, str]]:
    """Extract equality column pairs from an ON expression.

    Returns list of (left_table, left_column, right_table, right_column).
    Table values are None if not resolvable via aliases.
    """
    if on_expr is None:
        return []

    pairs: list[tuple[str | None, str, str | None, str]] = []
    for eq in on_expr.find_all(exp.EQ):
        left = eq.this
        right = eq.expression

        # Both sides must be Column references
        if not isinstance(left, exp.Column) or not isinstance(right, exp.Column):
            continue

        left_table = aliases.get(left.table.lower()) if left.table else None
        left_col = left.name
        right_table = aliases.get(right.table.lower()) if right.table else None
        right_col = right.name

        pairs.append((left_table, left_col, right_table, right_col))

    return pairs


def _resolve_join_relation(
    join: exp.Join,
    aliases: dict[str, str],
    tables_dict: dict,
) -> tuple[str | None, str | None, list, list]:
    """Extract source/target table and columns from a JOIN node.

    Returns (source_table, target_table, source_columns, target_columns).
    Tables are resolved to real names (or None if unknown/unmatched).
    """
    # Determine the join table
    join_table = join.this
    if _is_subquery(join_table):
        return None, None, [], []

    target_table = join_table.this.sql()  # the real table name in the JOIN
    join_alias = (join_table.alias or target_table).lower()

    # Update aliases with JOIN alias if not already present
    if join_alias not in aliases:
        aliases[join_alias] = target_table

    on_expr = join.args.get("on")
    if on_expr is None:
        # CROSS JOIN or JOIN without ON
        return None, target_table, [], []

    pairs = _extract_on_conditions(on_expr, aliases)

    # Determine source and target based on join type
    # For LEFT JOIN, left table (FROM) is source; for RIGHT JOIN, right is source
    side = join.args.get("side")

    # Build reverse alias lookup: table_name → (alias_lower, ...)
    # Actually, we need to figure out which side is FROM table vs JOIN table.
    # The FROM table alias is the one NOT matching the JOIN alias.

    source_columns: list[str] = []
    target_columns: list[str] = []

    encountered_table: str | None = None

    for left_table, left_col, right_table, right_col in pairs:
        # The side whose table matches the join alias is the target
        # The other side is the source (FROM table)
        if right_table and right_table.lower() == target_table.lower():
            # right side is the JOIN table
            source_columns.append(left_col if left_col else "")
            target_columns.append(right_col if right_col else "")
            if not encountered_table:
                encountered_table = left_table
        elif left_table and left_table.lower() == target_table.lower():
            # left side is the JOIN table
            source_columns.append(right_col if right_col else "")
            target_columns.append(left_col if left_col else "")
            if not encountered_table:
                encountered_table = right_table
        else:
            # Can't determine which side is which based on alias;
            # store as-is, first column pair defines source
            source_columns.append(left_col if left_col else "")
            target_columns.append(right_col if right_col else "")
            if not encountered_table:
                encountered_table = left_table or right_table

    source_table = encountered_table
    return source_table, target_table, source_columns, target_columns


def parse_join_relations(
    sql: str,
    tables_dict: dict,
    dialect: str = "mysql",
) -> tuple[list[DiscoveredRelation], list[str], int]:
    """Parse SQL SELECT statement(s) and extract table relations from JOINs.

    Args:
        sql: SQL query text (may contain multiple statements).
        tables_dict: dict of {lowercase_table_name: Table} from the project.
        dialect: SQL dialect for parsing.

    Returns:
        Tuple of (discovered_relations, unmatched_table_names, query_count).
    """
    try:
        parsed = list(sqlglot.parse(sql, dialect=dialect))
    except Exception as e:
        raise ValueError(f"SQL parse error: {e}")

    relations: list[DiscoveredRelation] = []
    all_unmatched: set[str] = set()
    query_count = 0

    for statement in parsed:
        if statement is None:
            continue
        if not isinstance(statement, exp.Select):
            continue

        query_count += 1
        aliases = _extract_aliases(statement)

        # Process each JOIN
        for join in statement.find_all(exp.Join):
            source_table, target_table, source_cols, target_cols = _resolve_join_relation(
                join, aliases, tables_dict
            )

            if target_table is None:
                continue  # subquery skip
            if not source_table:
                continue  # can't resolve source (CROSS JOIN, skipping for now)

            join_type = _join_type_string(join)

            # Resolve table names to project tables
            src_real = source_table
            tgt_real = target_table

            # Check if table names exist in project (case-insensitive)
            src_in_project = src_real.lower() in tables_dict
            tgt_in_project = tgt_real.lower() in tables_dict

            if not src_in_project:
                all_unmatched.add(src_real)
            if not tgt_in_project:
                all_unmatched.add(tgt_real)

            src_table = tgt_real if join_type == "RIGHT JOIN" else src_real
            tgt_table = src_real if join_type == "RIGHT JOIN" else tgt_real
            src_cols = target_cols if join_type == "RIGHT JOIN" else source_cols
            tgt_cols = source_cols if join_type == "RIGHT JOIN" else target_cols

            relation = DiscoveredRelation(
                temp_id=_make_temp_id(src_table, tgt_table, src_cols, tgt_cols),
                source_table=src_table,
                source_columns=src_cols,
                target_table=tgt_table,
                target_columns=tgt_cols,
                join_type=join_type,
                confidence=0.5 if join_type == "CROSS JOIN" else 1.0,
            )
            relations.append(relation)

    return relations, sorted(all_unmatched), query_count
