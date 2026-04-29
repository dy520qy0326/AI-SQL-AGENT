import pytest
import sqlglot

from app.query_relation.parser import DiscoveredRelation, parse_join_relations


def _empty_tables():
    return {}


def test_single_left_join():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id",
        tables,
    )
    assert count == 1
    assert len(rels) == 1
    r = rels[0]
    assert r.source_table == "users"
    assert r.target_table == "orders"
    assert r.source_columns == ["id"]
    assert r.target_columns == ["user_id"]
    assert r.join_type == "LEFT JOIN"
    assert r.confidence == 1.0


def test_inner_join():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users INNER JOIN orders ON users.id = orders.user_id",
        tables,
    )
    assert len(rels) == 1
    assert rels[0].join_type == "INNER JOIN"


def test_multiple_joins():

    tables = {
        "users": type("T", (), {"id": "u1"})(),
        "orders": type("T", (), {"id": "o1"})(),
        "products": type("T", (), {"id": "p1"})(),
    }
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u JOIN orders o ON u.id = o.user_id JOIN products p ON o.product_id = p.id",
        tables,
    )
    assert len(rels) == 2
    assert rels[0].source_table == "users"
    assert rels[0].target_table == "orders"
    assert rels[1].source_table == "orders"
    assert rels[1].target_table == "products"


def test_right_join():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM orders o RIGHT JOIN users u ON o.user_id = u.id",
        tables,
    )
    assert len(rels) == 1
    # RIGHT JOIN should be flipped: source=users, target=orders
    assert rels[0].source_table == "users"
    assert rels[0].target_table == "orders"
    assert rels[0].join_type == "RIGHT JOIN"


def test_cross_join_skipped():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users CROSS JOIN orders",
        tables,
    )
    assert len(rels) == 0  # CROSS JOIN without ON → no relation


def test_full_outer_join():

    tables = {"a": type("T", (), {"id": "a1"})(), "b": type("T", (), {"id": "b1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM a FULL OUTER JOIN b ON a.id = b.id",
        tables,
    )
    assert len(rels) == 1
    assert rels[0].join_type == "FULL OUTER JOIN"


def test_compound_on_condition():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u JOIN orders o ON u.id = o.user_id AND u.status = o.status",
        tables,
    )
    assert len(rels) == 1
    assert len(rels[0].source_columns) == 2
    assert rels[0].source_columns == ["id", "status"]
    assert rels[0].target_columns == ["user_id", "status"]


def test_table_alias_resolution():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    # Use different aliases
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users AS u JOIN orders AS o ON u.id = o.user_id",
        tables,
    )
    assert len(rels) == 1
    assert rels[0].source_table == "users"
    assert rels[0].target_table == "orders"


def test_self_join():

    tables = {"users": type("T", (), {"id": "u1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u1 JOIN users u2 ON u1.manager_id = u2.id",
        tables,
    )
    assert len(rels) == 1
    assert rels[0].source_table == "users"
    assert rels[0].target_table == "users"


def test_subquery_skipped():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u JOIN (SELECT * FROM orders) AS sub ON u.id = sub.user_id",
        tables,
    )
    assert len(rels) == 0  # subquery in JOIN should be skipped


def test_unmatched_tables():

    tables = {"users": type("T", (), {"id": "u1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u JOIN logs l ON u.id = l.user_id",
        tables,
    )
    assert "logs" in unmatched or "logs" in [u.lower() for u in unmatched]


def test_unmatched_both_tables():

    tables = {}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM a JOIN b ON a.id = b.id",
        tables,
    )
    assert len(unmatched) == 2


def test_multiple_statements():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})(),
              "products": type("T", (), {"id": "p1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u JOIN orders o ON u.id = o.user_id;\n"
        "SELECT * FROM orders o JOIN products p ON o.product_id = p.id",
        tables,
    )
    assert count == 2
    assert len(rels) == 2


def test_schema_qualified_names():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM public.users u JOIN public.orders o ON u.id = o.user_id",
        tables,
    )
    assert len(rels) == 1
    assert rels[0].source_table == "users"
    assert rels[0].target_table == "orders"


def test_invalid_sql():

    with pytest.raises(ValueError, match="SQL parse error"):
        parse_join_relations("CRATE TABLE t (id INT)", _empty_tables())


def test_empty_sql():

    rels, unmatched, count = parse_join_relations("", _empty_tables())
    assert len(rels) == 0
    assert len(unmatched) == 0
    assert count == 0


def test_no_join_in_sql():

    rels, unmatched, count = parse_join_relations("SELECT * FROM users", _empty_tables())
    assert len(rels) == 0


def test_using_clause():
    """USING clause produces an INNER JOIN with no explicit ON condition."""

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users JOIN orders USING (user_id)",
        tables,
    )
    # USING is treated as an INNER JOIN but without explicit EQ pairs in ON;
    # our parser currently only extracts EQ pairs from ON, so this is empty
    assert len(rels) == 0


def test_no_alias_implicit():

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users JOIN orders ON users.id = orders.user_id",
        tables,
    )
    assert len(rels) == 1
    assert rels[0].source_table == "users"
    assert rels[0].target_table == "orders"


def test_dialect_passthrough():
    """Different dialects should not affect basic join parsing."""

    tables = {"users": type("T", (), {"id": "u1"})(), "orders": type("T", (), {"id": "o1"})()}
    rels, unmatched, count = parse_join_relations(
        "SELECT * FROM users u JOIN orders o ON u.id = o.user_id",
        tables,
        dialect="postgres",
    )
    assert len(rels) == 1
