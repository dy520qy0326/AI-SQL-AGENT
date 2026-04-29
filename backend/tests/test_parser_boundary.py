"""Boundary tests for SQL DDL parser (Task 11).

Covers: large files, unknown dialect fallback, special characters in names,
and mixed edge cases not tested elsewhere.
"""

import time
import pytest
from app.parser.base import BaseParser
from app.parser.mysql import MySQLParser
from app.parser.postgres import PostgreSQLParser
from app.parser.dialect import detect_dialect


class ConcreteParser(BaseParser):
    """Concrete subclass of BaseParser for testing fallback behavior."""
    pass


@pytest.fixture
def mysql_parser():
    return MySQLParser()


@pytest.fixture
def pg_parser():
    return PostgreSQLParser()


@pytest.fixture
def base_parser():
    return ConcreteParser()


# ── Large File Performance (2000+ lines) ──────────────────────────────────────


class TestLargeFilePerformance:
    """Acceptance criteria: 2000 lines of DDL < 2 seconds."""

    @pytest.fixture
    def large_mysql_ddl(self):
        """Generate ~2000 lines of MySQL DDL."""
        table = """
CREATE TABLE `users` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) NOT NULL,
    `status` TINYINT(4) DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
        return "\n".join([table] * 210)  # ~210 * 10 lines ≈ 2100 lines

    @pytest.fixture
    def large_pg_ddl(self):
        """Generate ~2000 lines of PostgreSQL DDL."""
        table = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""
        return "\n".join([table] * 210)  # ~210 * 10 lines ≈ 2100 lines

    def test_mysql_2000_lines_under_2s(self, mysql_parser, large_mysql_ddl):
        line_count = large_mysql_ddl.count("\n") + 1
        assert line_count >= 2000, f"Only {line_count} lines, need ≥2000"

        start = time.perf_counter()
        result = mysql_parser.parse(large_mysql_ddl)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 2000, f"Parsing {line_count} lines took {elapsed:.1f}ms"
        assert len(result.tables) == 210
        assert result.errors == []

    def test_postgres_2000_lines_under_2s(self, pg_parser, large_pg_ddl):
        line_count = large_pg_ddl.count("\n") + 1
        assert line_count >= 2000, f"Only {line_count} lines, need ≥2000"

        start = time.perf_counter()
        result = pg_parser.parse(large_pg_ddl)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 2000, f"Parsing {line_count} lines took {elapsed:.1f}ms"
        assert len(result.tables) == 210
        assert result.errors == []


# ── Unknown Dialect Fallback ──────────────────────────────────────────────────


class TestUnknownDialectFallback:
    def test_detect_returns_mysql_by_default(self):
        """Unknown or ambiguous DDL defaults to mysql."""
        sql = "CREATE TABLE t (id INT)"
        assert detect_dialect(sql) == "mysql"

    def test_detect_with_no_sql_keywords(self):
        """Text with no SQL keywords defaults to mysql."""
        assert detect_dialect("Some random text with no SQL") == "mysql"

    def test_detect_serial_still_detects_postgres(self):
        """SERIAL keyword still detected as postgresql."""
        assert detect_dialect("id SERIAL") == "postgresql"

    def test_detect_mixed_features_defaults_to_earlier_rule(self):
        """When multiple dialect features present, detection order applies."""
        # Backtick rules come after SERIAL check
        sql = "id BIGSERIAL; `backtick`"
        assert detect_dialect(sql) == "postgresql"

    def test_unknown_type_does_not_crash(self, base_parser):
        """Unknown column type does not crash the parser."""
        sql = "CREATE TABLE t (id WHATEVER_UNKNOWN_TYPE)"
        result = base_parser.parse(sql)
        # Should either parse successfully or produce an error, but never crash
        assert isinstance(result.tables, list)
        assert isinstance(result.errors, list)

    def test_non_ddl_keywords_graceful(self, base_parser):
        """Statements with DDL-like but non-CREATE keywords are skipped."""
        sql = "ALTER TABLE t ADD COLUMN x INT;"
        result = base_parser.parse(sql)
        assert result.tables == []

    def test_drop_table_skipped(self, base_parser):
        """DROP TABLE statements are not parsed as CREATE TABLE."""
        sql = "DROP TABLE IF EXISTS t;"
        result = base_parser.parse(sql)
        assert result.tables == []

    def test_create_index_skipped(self, base_parser):
        """Standalone CREATE INDEX statements are not parsed."""
        sql = "CREATE INDEX idx_t_id ON t (id);"
        result = base_parser.parse(sql)
        assert result.tables == []

    def test_create_view_skipped(self, base_parser):
        """CREATE VIEW statements are not parsed."""
        sql = "CREATE VIEW v AS SELECT 1;"
        result = base_parser.parse(sql)
        assert result.tables == []

    def test_create_database_skipped(self, base_parser):
        """CREATE DATABASE statements are not parsed."""
        sql = "CREATE DATABASE testdb;"
        result = base_parser.parse(sql)
        assert result.tables == []


# ── Special Characters in Identifiers ─────────────────────────────────────────


class TestSpecialCharactersMySQL:
    def test_hyphen_in_quoted_table_name(self, mysql_parser):
        """Table name with hyphen in backtick quotes."""
        sql = "CREATE TABLE `my-table` (id INT)"
        result = mysql_parser.parse(sql)
        assert result.tables[0].name == "my-table"

    def test_hyphen_in_quoted_column_name(self, mysql_parser):
        """Column name with hyphen in backtick quotes."""
        sql = "CREATE TABLE t (`first-name` VARCHAR(50))"
        result = mysql_parser.parse(sql)
        assert result.tables[0].columns[0].name == "first-name"

    def test_space_in_quoted_table_name(self, mysql_parser):
        """Table name with space in backtick quotes."""
        sql = "CREATE TABLE `user profile` (id INT)"
        result = mysql_parser.parse(sql)
        assert result.tables[0].name == "user profile"

    def test_reserved_word_as_column_name(self, mysql_parser):
        """Reserved SQL keyword used as column name with backticks."""
        sql = "CREATE TABLE t (`select` INT, `from` VARCHAR(10), `where` DATE)"
        result = mysql_parser.parse(sql)
        cols = {c.name for c in result.tables[0].columns}
        assert "select" in cols
        assert "from" in cols
        assert "where" in cols

    def test_unicode_in_quoted_table_name(self, mysql_parser):
        """Table name with Chinese characters in backtick quotes."""
        sql = "CREATE TABLE `用户表` (id INT)"
        result = mysql_parser.parse(sql)
        assert result.tables[0].name == "用户表"

    def test_unicode_in_quoted_column_name(self, mysql_parser):
        """Column name with Chinese characters in backtick quotes."""
        sql = "CREATE TABLE t (`用户名` VARCHAR(50))"
        result = mysql_parser.parse(sql)
        assert result.tables[0].columns[0].name == "用户名"

    def test_number_prefix_quoted_table(self, mysql_parser):
        """Table name starting with number in backtick quotes."""
        sql = "CREATE TABLE `123data` (id INT)"
        result = mysql_parser.parse(sql)
        assert result.tables[0].name == "123data"

    def test_multiple_special_chars(self, mysql_parser):
        """Table and column with multiple special characters."""
        sql = "CREATE TABLE `t-1` (`col#1` INT, `col$2` VARCHAR(10), `col_3` DATE)"
        result = mysql_parser.parse(sql)
        cols = {c.name for c in result.tables[0].columns}
        assert "col#1" in cols
        assert "col$2" in cols
        assert "col_3" in cols

    def test_special_chars_with_all_features(self, mysql_parser):
        """Integration: special chars with full MySQL features."""
        sql = (
            "CREATE TABLE `order-items` (\n"
            "  `item-id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '商品ID',\n"
            "  `order-id` BIGINT(20) NOT NULL,\n"
            "  `unit-price` DECIMAL(10,2) NOT NULL DEFAULT 0.00,\n"
            "  PRIMARY KEY (`item-id`),\n"
            "  FOREIGN KEY (`order-id`) REFERENCES `orders`(`id`)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单项表'"
        )
        result = mysql_parser.parse(sql)
        t = result.tables[0]
        assert t.name == "order-items"
        assert t.comment == "订单项表"

        cols = {c.name: c for c in t.columns}
        assert cols["item-id"].auto_increment is True
        assert cols["item-id"].primary_key is True
        assert cols["item-id"].comment == "商品ID"
        assert cols["order-id"].nullable is False
        assert cols["unit-price"].type == "decimal"
        assert cols["unit-price"].default == "0.00"

        assert len(t.foreign_keys) == 1
        assert t.foreign_keys[0].columns == ["order-id"]
        assert t.foreign_keys[0].ref_table == "orders"


class TestSpecialCharactersPostgreSQL:
    def test_hyphen_in_quoted_table_name(self, pg_parser):
        """Table name with hyphen in double quotes."""
        sql = 'CREATE TABLE "my-table" (id INT)'
        result = pg_parser.parse(sql)
        assert result.tables[0].name == "my-table"

    def test_hyphen_in_quoted_column_name(self, pg_parser):
        """Column name with hyphen in double quotes."""
        sql = 'CREATE TABLE t ("first-name" VARCHAR(50))'
        result = pg_parser.parse(sql)
        assert result.tables[0].columns[0].name == "first-name"

    def test_space_in_quoted_table_name(self, pg_parser):
        """Table name with space in double quotes."""
        sql = 'CREATE TABLE "user profile" (id INT)'
        result = pg_parser.parse(sql)
        assert result.tables[0].name == "user profile"

    def test_reserved_word_as_column_name(self, pg_parser):
        """Reserved SQL keyword used as column name with double quotes."""
        sql = 'CREATE TABLE t ("select" INT, "from" VARCHAR(10), "where" DATE)'
        result = pg_parser.parse(sql)
        cols = {c.name for c in result.tables[0].columns}
        assert "select" in cols
        assert "from" in cols
        assert "where" in cols

    def test_unicode_in_quoted_table_name(self, pg_parser):
        """Table name with Chinese characters in double quotes."""
        sql = 'CREATE TABLE "用户表" (id INT)'
        result = pg_parser.parse(sql)
        assert result.tables[0].name == "用户表"

    def test_unicode_in_quoted_column_name(self, pg_parser):
        """Column name with Chinese characters in double quotes."""
        sql = 'CREATE TABLE t ("用户名" VARCHAR(50))'
        result = pg_parser.parse(sql)
        assert result.tables[0].columns[0].name == "用户名"

    def test_number_prefix_quoted_table(self, pg_parser):
        """Table name starting with number in double quotes."""
        sql = 'CREATE TABLE "123data" (id INT)'
        result = pg_parser.parse(sql)
        assert result.tables[0].name == "123data"

    def test_special_chars_with_serial_and_comment(self, pg_parser):
        """Integration: special chars with full PG features."""
        sql = (
            'CREATE TABLE "order-items" (\n'
            '  "item-id" SERIAL PRIMARY KEY,\n'
            '  "order-id" INT NOT NULL,\n'
            '  "unit-price" DECIMAL(10,2) NOT NULL DEFAULT 0.00\n'
            ');\n'
            "COMMENT ON TABLE \"order-items\" IS '订单项表';\n"
            "COMMENT ON COLUMN \"order-items\".\"item-id\" IS '商品ID'"
        )
        result = pg_parser.parse(sql)
        t = result.tables[0]
        assert t.name == "order-items"
        assert t.comment == "订单项表"

        cols = {c.name: c for c in t.columns}
        assert cols["item-id"].type == "integer"
        assert cols["item-id"].auto_increment is True
        assert cols["item-id"].primary_key is True
        assert cols["item-id"].comment == "商品ID"
        assert cols["unit-price"].type == "decimal"


# ── Malformed SQL — Additional Edge Cases ─────────────────────────────────────


class TestMalformedDDLEdgeCases:
    def test_missing_closing_parenthesis(self, base_parser):
        """Missing closing parenthesis in table def."""
        sql = "CREATE TABLE t (id INT, name VARCHAR(50)"
        result = base_parser.parse(sql)
        # Should not crash; either errors or produces partial results
        assert isinstance(result.tables, list)
        assert isinstance(result.errors, list)

    def test_extra_closing_parenthesis(self, base_parser):
        """Extra closing parenthesis."""
        sql = "CREATE TABLE t (id INT))"
        result = base_parser.parse(sql)
        assert isinstance(result.tables, list)
        assert isinstance(result.errors, list)

    def test_missing_column_type(self, base_parser):
        """Column definition without a type."""
        sql = "CREATE TABLE t (id)"
        result = base_parser.parse(sql)
        # sqlglot may or may not handle this; no crash
        assert isinstance(result.tables, list)
        assert isinstance(result.errors, list)

    def test_missing_table_name(self, base_parser):
        """CREATE TABLE with no name."""
        sql = "CREATE TABLE (id INT)"
        result = base_parser.parse(sql)
        assert isinstance(result.tables, list)
        assert isinstance(result.errors, list)

    def test_missing_semicolons_large_mix(self, base_parser):
        """Mix of semicolons and missing semicolons."""
        sql = (
            "CREATE TABLE a (id INT)\n"
            "CREATE TABLE b (id INT);\n"
            "CREATE TABLE c (id INT)\n"
            "CREATE TABLE d (id INT);\n"
            "CREATE TABLE e (id INT)"
        )
        result = base_parser.parse(sql)
        assert len(result.tables) == 5

    def test_repeated_create_table(self, base_parser):
        """CREATE TABLE keyword appearing in a comment should not split."""
        sql = (
            "-- CREATE TABLE should be ignored\n"
            "CREATE TABLE t (id INT);"
        )
        result = base_parser.parse(sql)
        assert len(result.tables) == 1

    def test_trailing_comma_in_column_list(self, mysql_parser):
        """Trailing comma after last column definition."""
        sql = "CREATE TABLE t (id INT, name VARCHAR(50),)"
        result = mysql_parser.parse(sql)
        # sqlglot may or may not handle this; should not crash
        assert isinstance(result.tables, list)

    def test_very_long_table_name(self, mysql_parser):
        """Very long quoted table name (up to 64 chars in MySQL)."""
        name = "a" * 64
        sql = f"CREATE TABLE `{name}` (id INT)"
        result = mysql_parser.parse(sql)
        assert result.tables[0].name == name


# ── Mixed DDL Statements ──────────────────────────────────────────────────────


class TestMixedDDLStatements:
    def test_mix_create_table_and_other_ddl(self, mysql_parser):
        """Mix of CREATE TABLE, ALTER TABLE, and other DDL statements."""
        sql = (
            "CREATE TABLE t1 (id INT);\n"
            "ALTER TABLE t1 ADD COLUMN x INT;\n"
            "CREATE TABLE t2 (id INT);\n"
            "CREATE INDEX idx_t1_id ON t1(id);\n"
            "CREATE TABLE t3 (id INT);\n"
        )
        result = mysql_parser.parse(sql)
        assert len(result.tables) == 3
        assert [t.name for t in result.tables] == ["t1", "t2", "t3"]

    def test_mix_create_and_insert(self, mysql_parser):
        """Mix of CREATE TABLE and INSERT statements."""
        sql = (
            "CREATE TABLE users (id INT, name VARCHAR(50));\n"
            "INSERT INTO users VALUES (1, 'Alice');\n"
            "CREATE TABLE posts (id INT, title VARCHAR(100));\n"
        )
        result = mysql_parser.parse(sql)
        assert len(result.tables) == 2
        assert result.tables[0].name == "users"
        assert result.tables[1].name == "posts"

    def test_mix_multiple_dialects(self, mysql_parser):
        """MySQL parser handles PG-specific syntax gracefully."""
        sql = (
            "CREATE TABLE t1 (id INT);\n"
            "CREATE TABLE t2 (id SERIAL PRIMARY KEY);\n"
        )
        result = mysql_parser.parse(sql)
        # The MySQL parser will try to parse PG SERIAL in mysql dialect
        # It may or may not succeed; either way no crash
        assert isinstance(result.tables, list)
        assert isinstance(result.errors, list)

    def test_empty_statements_between_valid(self, base_parser):
        """Empty statements (;;) between valid ones."""
        sql = (
            "CREATE TABLE a (id INT);;\n"
            "CREATE TABLE b (id INT);\n"
            ";\n"
            "CREATE TABLE c (id INT);"
        )
        result = base_parser.parse(sql)
        assert len(result.tables) == 3


# ── Data Type Edge Cases ──────────────────────────────────────────────────────


class TestDataTypeEdgeCases:
    def test_very_long_varchar(self, mysql_parser):
        """VARCHAR with maximum length."""
        sql = "CREATE TABLE t (name VARCHAR(65535))"
        result = mysql_parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "varchar"
        assert col.length == 65535

    def test_numeric_types(self, mysql_parser):
        """Various numeric types."""
        sql = (
            "CREATE TABLE t (\n"
            "  a TINYINT,\n"
            "  b SMALLINT,\n"
            "  c MEDIUMINT,\n"
            "  d INT,\n"
            "  e BIGINT,\n"
            "  f FLOAT,\n"
            "  g DOUBLE,\n"
            "  h DECIMAL(10,2)\n"
            ")"
        )
        result = mysql_parser.parse(sql)
        cols = {c.name: c for c in result.tables[0].columns}
        assert cols["a"].type == "tinyint"
        assert cols["b"].type == "smallint"
        assert cols["c"].type == "mediumint"
        assert cols["d"].type == "int"
        assert cols["e"].type == "bigint"
        assert cols["f"].type == "float"
        assert cols["g"].type == "double"
        assert cols["h"].type == "decimal"

    def test_boolean_variants(self, mysql_parser):
        """BOOL and BOOLEAN as synonyms for TINYINT(1)."""
        sql = "CREATE TABLE t (a BOOL, b BOOLEAN)"
        result = mysql_parser.parse(sql)
        cols = {c.name: c for c in result.tables[0].columns}
        # sqlglot normalizes BOOL/BOOLEAN
        assert cols["a"].type in ("tinyint", "boolean", "bool")
        assert cols["b"].type in ("tinyint", "boolean", "bool")

    def test_multiple_default_expressions(self, mysql_parser):
        """Various DEFAULT expressions."""
        sql = (
            "CREATE TABLE t (\n"
            "  a INT DEFAULT 0,\n"
            "  b VARCHAR(10) DEFAULT 'hello',\n"
            "  c DECIMAL(10,2) DEFAULT 99.99,\n"
            "  d BOOLEAN DEFAULT TRUE,\n"
            "  e DATE DEFAULT NULL\n"
            ")"
        )
        result = mysql_parser.parse(sql)
        cols = {c.name: c for c in result.tables[0].columns}
        assert cols["a"].default == "0"
        assert cols["b"].default == "hello"
        assert cols["d"].default is not None  # TRUE may normalize to "1" or "true"
        assert cols["e"].default == "NULL"
