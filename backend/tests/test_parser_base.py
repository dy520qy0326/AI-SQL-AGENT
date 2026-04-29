"""Tests for parser base module: BaseParser, statement splitting, and dialect detection."""

import pytest
from app.parser.base import BaseParser
from app.parser.dialect import detect_dialect


class ConcreteParser(BaseParser):
    """Concrete subclass of BaseParser for testing."""
    pass


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def parser():
    return ConcreteParser()


MULTI_STMT_SQL = """
CREATE TABLE users (
    id INT PRIMARY KEY
);

CREATE TABLE posts (
    id INT PRIMARY KEY,
    user_id INT REFERENCES users(id)
);

CREATE TABLE comments (
    id INT PRIMARY KEY
);
"""


# ── Statement Splitting ───────────────────────────────────────────────────────


class TestParseStatements:
    def test_single_statement(self, parser):
        stmts = parser._parse_statements("CREATE TABLE t (id INT);")
        assert len(stmts) == 1
        assert stmts[0].upper().startswith("CREATE TABLE T")

    def test_multiple_statements_with_semicolons(self, parser):
        stmts = parser._parse_statements(MULTI_STMT_SQL)
        assert len(stmts) == 3
        assert all("CREATE TABLE" in s.upper() for s in stmts)

    def test_empty_input(self, parser):
        assert parser._parse_statements("") == []

    def test_whitespace_only_input(self, parser):
        assert parser._parse_statements("   \n  \n  ") == []

    def test_only_comments(self, parser):
        sql = "-- This is a comment\n-- Another comment"
        assert parser._parse_statements(sql) == []

    def test_block_comments_removed(self, parser):
        sql = "/* block comment */ CREATE TABLE t (id INT);"
        stmts = parser._parse_statements(sql)
        assert len(stmts) == 1

    def test_missing_semicolons_split_by_create(self, parser):
        """When semicolons are missing, split by CREATE keyword."""
        sql = """CREATE TABLE a (id INT)
CREATE TABLE b (id INT)
CREATE TABLE c (id INT)"""
        stmts = parser._parse_statements(sql)
        assert len(stmts) == 3

    def test_mixed_semicolons_and_missing(self, parser):
        """Mix of semicolons and missing — should still split correctly."""
        sql = """CREATE TABLE a (id INT);
CREATE TABLE b (id INT)
CREATE TABLE c (id INT);"""
        stmts = parser._parse_statements(sql)
        assert len(stmts) == 3

    def test_comment_inside_string_not_stripped(self, parser):
        """-- inside a string literal should not be treated as a comment."""
        sql = "CREATE TABLE t (name VARCHAR(10) DEFAULT '--not-a-comment');"
        stmts = parser._parse_statements(sql)
        assert len(stmts) == 1
        assert "--not-a-comment" in stmts[0]

    def test_partial_create_keyword_in_identifier(self, parser):
        """The word CREATE appearing in an identifier should not split."""
        sql = "CREATE TABLE t (created_at INT); CREATE TABLE u (id INT);"
        stmts = parser._parse_statements(sql)
        assert len(stmts) == 2


# ── Dialect Detection ─────────────────────────────────────────────────────────


class TestDetectDialect:
    def test_explicit_mysql(self):
        assert detect_dialect("", explicit="mysql") == "mysql"

    def test_explicit_postgresql(self):
        assert detect_dialect("", explicit="postgresql") == "postgresql"

    def test_auto_increment_detected_as_mysql(self):
        sql = "CREATE TABLE t (id INT AUTO_INCREMENT)"
        assert detect_dialect(sql) == "mysql"

    def test_serial_detected_as_postgresql(self):
        sql = "CREATE TABLE t (id SERIAL PRIMARY KEY)"
        assert detect_dialect(sql) == "postgresql"

    def test_bigserial_detected_as_postgresql(self):
        sql = "CREATE TABLE t (id BIGSERIAL PRIMARY KEY)"
        assert detect_dialect(sql) == "postgresql"

    def test_type_cast_detected_as_postgresql(self):
        sql = "SELECT id::INT FROM t"
        assert detect_dialect(sql) == "postgresql"

    def test_backtick_detected_as_mysql(self):
        sql = "CREATE TABLE `users` (id INT)"
        assert detect_dialect(sql) == "mysql"

    def test_default_to_mysql(self):
        sql = "CREATE TABLE t (id INT)"
        assert detect_dialect(sql) == "mysql"

    def test_empty_input_defaults_to_mysql(self):
        assert detect_dialect("") == "mysql"
        assert detect_dialect("   ") == "mysql"

    def test_none_explicit_no_text_defaults_to_mysql(self):
        assert detect_dialect("", None) == "mysql"

    def test_none_explicit_with_text_detects(self):
        sql = "CREATE TABLE t (id SERIAL PRIMARY KEY)"
        assert detect_dialect(sql, None) == "postgresql"


# ── Parse — Basic Flow ────────────────────────────────────────────────────────


class TestParse:
    def test_empty_input_returns_empty_result(self, parser):
        result = parser.parse("")
        assert result.tables == []
        assert result.errors == []
        assert result.dialect == "mysql"

    def test_whitespace_only_returns_empty_result(self, parser):
        result = parser.parse("   \n\n  ")
        assert result.tables == []
        assert result.errors == []

    def test_parse_sets_dialect(self, parser):
        result = parser.parse("CREATE TABLE t (id INT AUTO_INCREMENT);")
        assert result.dialect == "mysql"

    def test_parse_postgresql_dialect(self, parser):
        result = parser.parse("CREATE TABLE t (id SERIAL PRIMARY KEY);")
        assert result.dialect == "postgresql"

    def test_parse_no_errors_on_valid_sql(self, parser):
        result = parser.parse("CREATE TABLE t (id INT);")
        assert result.errors == []

    def test_parse_multiple_tables(self, parser):
        result = parser.parse(MULTI_STMT_SQL)
        assert result.dialect == "mysql"
        assert len(result.tables) == 3
        assert [t.name for t in result.tables] == ["users", "posts", "comments"]


# ── CREATE TABLE Parsing (Task 3) ───────────────────────────────────────────


class TestCreateTableParsing:
    def test_table_name(self, parser):
        result = parser.parse("CREATE TABLE users (id INT);")
        t = result.tables[0]
        assert t.name == "users"

    def test_table_name_with_schema(self, parser):
        result = parser.parse("CREATE TABLE public.users (id INT);")
        t = result.tables[0]
        assert t.name == "users"
        assert t.schema_ == "public"

    def test_column_name_and_type(self, parser):
        result = parser.parse("CREATE TABLE t (id INT);")
        col = result.tables[0].columns[0]
        assert col.name == "id"
        assert col.type == "int"

    def test_varchar_with_length(self, parser):
        result = parser.parse("CREATE TABLE t (name VARCHAR(255));")
        col = result.tables[0].columns[0]
        assert col.type == "varchar"
        assert col.length == 255

    def test_decimal_with_precision(self, parser):
        result = parser.parse("CREATE TABLE t (price DECIMAL(10, 2));")
        col = result.tables[0].columns[0]
        assert col.type == "decimal"
        assert col.length == 10

    def test_no_length_types(self, parser):
        sql = "CREATE TABLE t (a TEXT, b BOOLEAN, c JSON);"
        result = parser.parse(sql)
        cols = result.tables[0].columns
        assert cols[0].type == "text"
        assert cols[0].length is None
        assert cols[1].type == "boolean"
        assert cols[1].length is None
        assert cols[2].type == "json"
        assert cols[2].length is None

    def test_not_null(self, parser):
        result = parser.parse("CREATE TABLE t (id INT NOT NULL);")
        assert result.tables[0].columns[0].nullable is False

    def test_nullable_default(self, parser):
        result = parser.parse("CREATE TABLE t (id INT);")
        assert result.tables[0].columns[0].nullable is True

    def test_column_level_primary_key(self, parser):
        result = parser.parse("CREATE TABLE t (id INT PRIMARY KEY);")
        col = result.tables[0].columns[0]
        assert col.primary_key is True
        assert col.nullable is False

    def test_composite_primary_key(self, parser):
        sql = "CREATE TABLE t (a INT, b INT, PRIMARY KEY (a, b));"
        result = parser.parse(sql)
        cols = {c.name: c for c in result.tables[0].columns}
        assert cols["a"].primary_key is True
        assert cols["b"].primary_key is True

    def test_default_string(self, parser):
        result = parser.parse(
            "CREATE TABLE t (status VARCHAR(10) DEFAULT 'active');"
        )
        assert result.tables[0].columns[0].default == "active"

    def test_default_number(self, parser):
        result = parser.parse("CREATE TABLE t (age INT DEFAULT 18);")
        assert result.tables[0].columns[0].default == "18"

    def test_default_null(self, parser):
        result = parser.parse(
            "CREATE TABLE t (deleted_at TIMESTAMP DEFAULT NULL);"
        )
        assert result.tables[0].columns[0].default == "NULL"

    def test_multiple_columns(self, parser):
        sql = """CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255),
            age INT DEFAULT 0
        );"""
        result = parser.parse(sql)
        cols = result.tables[0].columns
        assert len(cols) == 4
        assert cols[0].name == "id"
        assert cols[0].type == "int"
        assert cols[0].length is None
        assert cols[0].nullable is False
        assert cols[0].primary_key is True
        assert cols[1].name == "name"
        assert cols[1].type == "varchar"
        assert cols[1].length == 100
        assert cols[1].nullable is False
        assert cols[2].name == "email"
        assert cols[2].type == "varchar"
        assert cols[2].length == 255
        assert cols[2].nullable is True
        assert cols[3].name == "age"
        assert cols[3].type == "int"
        assert cols[3].length is None
        assert cols[3].default == "0"
        assert cols[3].nullable is True


# ── Foreign Key Parsing (Task 4) ──────────────────────────────────────────


class TestForeignKeyParsing:
    def test_column_level_fk(self, parser):
        """col INT REFERENCES ref_t(ref_col)"""
        result = parser.parse(
            "CREATE TABLE t (id INT REFERENCES other(other_id));"
        )
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["id"]
        assert fks[0].ref_table == "other"
        assert fks[0].ref_columns == ["other_id"]

    def test_table_level_fk(self, parser):
        """FOREIGN KEY (col) REFERENCES ref_t(ref_col)"""
        result = parser.parse(
            "CREATE TABLE t (id INT, FOREIGN KEY (id) REFERENCES other(other_id));"
        )
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["id"]
        assert fks[0].ref_table == "other"
        assert fks[0].ref_columns == ["other_id"]

    def test_composite_fk(self, parser):
        """FOREIGN KEY (a, b) REFERENCES ref(c, d)"""
        sql = (
            "CREATE TABLE t (a INT, b INT, "
            "FOREIGN KEY (a, b) REFERENCES ref(c, d));"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["a", "b"]
        assert fks[0].ref_table == "ref"
        assert fks[0].ref_columns == ["c", "d"]

    def test_multiple_fks(self, parser):
        """Multiple table-level FOREIGN KEY constraints."""
        sql = (
            "CREATE TABLE t ("
            "  a INT, b INT, c INT,"
            "  FOREIGN KEY (a) REFERENCES x(c),"
            "  FOREIGN KEY (b) REFERENCES y(d)"
            ");"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 2
        assert fks[0].columns == ["a"]
        assert fks[0].ref_table == "x"
        assert fks[0].ref_columns == ["c"]
        assert fks[1].columns == ["b"]
        assert fks[1].ref_table == "y"
        assert fks[1].ref_columns == ["d"]

    def test_mixed_column_and_table_fk(self, parser):
        """Column-level + table-level FKs in the same table."""
        sql = (
            "CREATE TABLE t ("
            "  a INT REFERENCES x(a_id),"
            "  b INT,"
            "  FOREIGN KEY (b) REFERENCES y(b_id)"
            ");"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 2
        assert fks[0].columns == ["a"]
        assert fks[0].ref_table == "x"
        assert fks[1].columns == ["b"]
        assert fks[1].ref_table == "y"

    def test_no_fk(self, parser):
        """Table with no foreign keys returns empty fk list."""
        result = parser.parse("CREATE TABLE t (id INT PRIMARY KEY);")
        assert result.tables[0].foreign_keys == []
