"""Tests for the schema diff engine."""

import json
import os

import pytest

from app.diff.engine import compute_diff, _levenshtein, _match_tables


def _load_fixture(name: str) -> list[dict]:
    """Parse a SQL fixture and return its table list as dicts."""
    from app.parser import MySQLParser

    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(fixture_path) as f:
        sql = f.read()
    parser = MySQLParser()
    result = parser.parse(sql)
    return [t.model_dump() for t in result.tables]


# ── Levenshtein ──────────────────────────────────────────────────────


class TestLevenshtein:
    def test_exact_match(self):
        assert _levenshtein("users", "users") == 0

    def test_one_insertion(self):
        assert _levenshtein("users", "userss") == 1

    def test_one_deletion(self):
        assert _levenshtein("users", "user") == 1

    def test_one_substitution(self):
        assert _levenshtein("users", "useds") == 1

    def test_completely_different(self):
        assert _levenshtein("abc", "xyz") == 3

    def test_empty_strings(self):
        assert _levenshtein("", "") == 0
        assert _levenshtein("abc", "") == 3
        assert _levenshtein("", "abc") == 3


# ── Basic engine tests ───────────────────────────────────────────────


class TestComputeDiff:
    def test_no_changes(self):
        """Identical inputs produce empty diff."""
        tables = [
            {"name": "users", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []},
        ]
        result = compute_diff(tables, tables)
        assert len(result.tables_added) == 0
        assert len(result.tables_removed) == 0
        assert len(result.fields_modified) == 0
        assert result.breaking_changes is False
        assert result.summary_stats["tables"]["added"] == 0
        assert result.summary_stats["fields"]["modified"] == 0

    def test_table_added(self):
        """New table in new version is detected."""
        old = [{"name": "a", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        new = [{"name": "a", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []},
               {"name": "b", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["tables"]["added"] == 1
        assert len(result.tables_added) == 1
        assert result.tables_added[0]["name"] == "b"

    def test_table_removed(self):
        """Removed table is detected (breaking)."""
        old = [{"name": "a", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []},
               {"name": "b", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        new = [{"name": "a", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["tables"]["removed"] == 1
        assert result.breaking_changes is True
        assert len(result.breaking_details) >= 1

    def test_table_renamed_by_edit_distance(self):
        """Renamed table detected via edit distance + field overlap."""
        old = [{"name": "addresses", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}, {"name": "line", "type": "varchar"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "user_addresses", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}, {"name": "line", "type": "varchar"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["tables"]["renamed"] == 1
        assert len(result.tables_renamed) == 1
        assert result.tables_renamed[0]["old_name"] == "addresses"
        assert result.tables_renamed[0]["new_name"] == "user_addresses"

    def test_field_added(self):
        """New field in existing table is detected."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "name", "type": "varchar"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["fields"]["added"] == 1
        assert result.fields_added[0]["field"] == "name"

    def test_field_removed(self):
        """Removed field is detected (breaking)."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "old_col", "type": "varchar"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["fields"]["removed"] == 1
        assert result.breaking_changes is True

    def test_field_type_changed(self):
        """Field type change is detected."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "bigint"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["fields"]["modified"] == 1
        assert "type" in result.fields_modified[0]["changes"]

    def test_field_length_changed(self):
        """Field length change is detected."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "name", "type": "varchar", "length": 100}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "name", "type": "varchar", "length": 255}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["fields"]["modified"] == 1
        assert "length" in result.fields_modified[0]["changes"]

    def test_nullable_changed_not_null_to_null(self):
        """NOT NULL → NULL is breaking."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "x", "type": "int", "nullable": False}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "x", "type": "int", "nullable": True}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["fields"]["modified"] == 1
        assert result.breaking_changes is True

    def test_default_changed(self):
        """Default value change is detected."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "s", "type": "varchar", "default": "pending"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "s", "type": "varchar", "default": "active"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["fields"]["modified"] == 1
        assert "default" in result.fields_modified[0]["changes"]

    def test_index_added(self):
        """New index is detected."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [{"name": "idx_id", "unique": False, "columns": ["id"]}], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["indexes"]["added"] == 1

    def test_index_removed(self):
        """Removed index is detected (breaking)."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [{"name": "idx_id", "unique": False, "columns": ["id"]}], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["indexes"]["removed"] == 1
        assert result.breaking_changes is True

    def test_foreign_key_added(self):
        """New FK is detected."""
        old = [{"name": "orders", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "orders", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}], "indexes": [], "foreign_keys": [{"columns": ["user_id"], "ref_table": "users", "ref_columns": ["id"]}]}]
        result = compute_diff(old, new)
        assert result.summary_stats["relations"]["added"] == 1

    def test_foreign_key_removed(self):
        """Removed FK is detected (breaking)."""
        old = [{"name": "orders", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}], "indexes": [], "foreign_keys": [{"columns": ["user_id"], "ref_table": "users", "ref_columns": ["id"]}]}]
        new = [{"name": "orders", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "user_id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["relations"]["removed"] == 1
        assert result.breaking_changes is True


# ── Breaking change detection ────────────────────────────────────────


class TestBreakingChanges:
    def test_type_narrowing_int_to_tinyint(self):
        """int → smallint/tinyint is narrowing → breaking."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "x", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "x", "type": "smallint"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.breaking_changes is True

    def test_type_expansion_int_to_bigint(self):
        """int → bigint is NOT breaking (widening)."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "x", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "x", "type": "bigint"}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.breaking_changes is False

    def test_length_shortening(self):
        """varchar(255) → varchar(100) is breaking."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "n", "type": "varchar", "length": 255}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "n", "type": "varchar", "length": 100}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.breaking_changes is True

    def test_length_expansion(self):
        """varchar(100) → varchar(255) is NOT breaking."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "n", "type": "varchar", "length": 100}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "n", "type": "varchar", "length": 255}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.breaking_changes is False


# ── Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_both(self):
        """Both versions empty produces no diff."""
        result = compute_diff([], [])
        assert result.summary_stats["tables"]["added"] == 0
        assert result.summary_stats["tables"]["removed"] == 0

    def test_empty_old(self):
        """Empty old → all new tables as added."""
        new = [{"name": "a", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        result = compute_diff([], new)
        assert result.summary_stats["tables"]["added"] == 1

    def test_empty_new(self):
        """Empty new → all old tables as removed (breaking)."""
        old = [{"name": "a", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, [])
        assert result.summary_stats["tables"]["removed"] == 1
        assert result.breaking_changes is True

    def test_lots_of_tables_no_changes(self):
        """Many identical tables produce no false positives."""
        old = [{"name": f"t{i}", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []} for i in range(10)]
        result = compute_diff(old, old)
        assert result.summary_stats["tables"]["added"] == 0
        assert result.summary_stats["tables"]["removed"] == 0
        assert result.summary_stats["tables"]["renamed"] == 0

    def test_case_sensitive_table_names(self):
        """Table matching should be case-insensitive."""
        old = [{"name": "Users", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        new = [{"name": "users", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        assert result.summary_stats["tables"]["renamed"] == 0  # matched, not renamed

    def test_summary_stats_accurate(self):
        """Summary statistics should match actual change counts."""
        old = [{"name": "a", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []},
               {"name": "b", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "a", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "bigint"}], "indexes": [], "foreign_keys": []},
               {"name": "b", "schema_": "", "comment": "", "columns": [{"name": "id", "type": "int"}, {"name": "x", "type": "varchar"}], "indexes": [], "foreign_keys": []},
               {"name": "c", "schema_": "", "comment": "", "columns": [], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        s = result.summary_stats
        assert s["tables"]["added"] == 1
        assert s["tables"]["removed"] == 0
        assert s["fields"]["added"] == 1
        assert s["fields"]["modified"] == 1

    def test_field_rename_not_false_positive(self):
        """Field at same position with same type should be matched, not appear as removed+added."""
        old = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "old_name", "type": "varchar", "ordinal_position": 1}, {"name": "id", "type": "int", "ordinal_position": 2}], "indexes": [], "foreign_keys": []}]
        new = [{"name": "t", "schema_": "", "comment": "", "columns": [{"name": "new_name", "type": "varchar", "ordinal_position": 1}, {"name": "id", "type": "int", "ordinal_position": 2}], "indexes": [], "foreign_keys": []}]
        result = compute_diff(old, new)
        # Should detect as rename, NOT as remove + add
        assert result.summary_stats["fields"]["renamed"] == 1, "Should detect rename"
        assert result.summary_stats["fields"]["removed"] == 0, "Should not be false removed"
        assert result.summary_stats["fields"]["added"] == 0, "Should not be false added"


# ── Fixture-based integration tests ──────────────────────────────────


class TestFixtureBased:
    def test_ecommerce_v1_v2_end_to_end(self):
        """Full diff between ecommerce V1 and V2."""
        old_tables = _load_fixture("sample_ecommerce.sql")
        new_tables = _load_fixture("sample_ecommerce_v2.sql")
        result = compute_diff(old_tables, new_tables)

        s = result.summary_stats

        # Each assertion with a clear error message
        assert s["tables"]["added"] == 1, "Should detect coupons as new table"
        assert s["tables"]["removed"] == 2, "Should detect inventory + shipping_log as removed"
        assert s["fields"]["added"] == 1, "Should detect orders.coupon_id"
        assert s["fields"]["removed"] == 1, "Should detect payments.method removal"
        assert s["fields"]["modified"] >= 2, "Should detect type/length changes"
        assert result.breaking_changes is True, "Removing tables and fields is breaking"

        # Verify specific changes
        added_tables = [t["name"] for t in result.tables_added]
        assert "coupons" in added_tables

        removed_tables = [t["name"] for t in result.tables_removed]
        assert "inventory" in removed_tables
        assert "shipping_log" in removed_tables

        removed_fields = [(f["table"], f["field"]) for f in result.fields_removed]
        assert ("payments", "method") in removed_fields

        added_fields = [(f["table"], f["field"]) for f in result.fields_added]
        assert ("orders", "coupon_id") in added_fields
