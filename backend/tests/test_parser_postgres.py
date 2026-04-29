"""Tests for PostgreSQLParser — PostgreSQL dialect-specific parsing."""

import pytest
from app.parser.postgres import PostgreSQLParser


@pytest.fixture
def parser():
    return PostgreSQLParser()


# ── Dialect ─────────────────────────────────────────────────────────────────────


class TestDialect:
    def test_dialect_is_postgresql(self, parser):
        assert parser.dialect == "postgresql"

    def test_auto_detect_from_serial(self, parser):
        sql = "CREATE TABLE t (id SERIAL PRIMARY KEY)"
        result = parser.parse(sql)
        assert result.dialect == "postgresql"

    def test_auto_detect_from_bigserial(self, parser):
        sql = "CREATE TABLE t (id BIGSERIAL PRIMARY KEY)"
        result = parser.parse(sql)
        assert result.dialect == "postgresql"

    def test_auto_detect_from_type_cast(self, parser):
        sql = "CREATE TABLE t (id INT DEFAULT nextval('seq'::regclass))"
        result = parser.parse(sql)
        assert result.dialect == "postgresql"


# ── SERIAL Types ────────────────────────────────────────────────────────────────


class TestSerialTypes:
    def test_serial_becomes_integer_auto_increment(self, parser):
        sql = "CREATE TABLE t (id SERIAL)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "integer"
        assert col.auto_increment is True

    def test_bigserial_becomes_bigint_auto_increment(self, parser):
        sql = "CREATE TABLE t (id BIGSERIAL)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "bigint"
        assert col.auto_increment is True

    def test_smallserial_becomes_smallint_auto_increment(self, parser):
        sql = "CREATE TABLE t (id SMALLSERIAL)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "smallint"
        assert col.auto_increment is True

    def test_serial_with_primary_key(self, parser):
        sql = "CREATE TABLE t (id SERIAL PRIMARY KEY)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "integer"
        assert col.auto_increment is True
        assert col.primary_key is True
        assert col.nullable is False

    def test_mixed_serial_and_regular(self, parser):
        sql = "CREATE TABLE t (id SERIAL, name VARCHAR(100), count INT)"
        result = parser.parse(sql)
        cols = result.tables[0].columns
        assert cols[0].type == "integer"
        assert cols[0].auto_increment is True
        assert cols[1].auto_increment is False
        assert cols[1].type == "varchar"
        assert cols[2].auto_increment is False
        assert cols[2].type == "int"


# ── Double-quote Quoting ────────────────────────────────────────────────────────


class TestDoubleQuoteQuoting:
    def test_quoted_table_name(self, parser):
        sql = 'CREATE TABLE "users" (id INT)'
        result = parser.parse(sql)
        assert result.tables[0].name == "users"

    def test_quoted_column_name(self, parser):
        sql = 'CREATE TABLE t ("user name" VARCHAR(100))'
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.name == "user name"

    def test_quoted_schema_table(self, parser):
        sql = 'CREATE TABLE "mydb"."users" (id INT)'
        result = parser.parse(sql)
        t = result.tables[0]
        assert t.name == "users"
        assert t.schema_ == "mydb"


# ── PostgreSQL-Specific Types ───────────────────────────────────────────────────


class TestPostgresTypes:
    def test_uuid_type(self, parser):
        sql = "CREATE TABLE t (id UUID PRIMARY KEY)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "uuid"

    def test_jsonb_type(self, parser):
        sql = "CREATE TABLE t (data JSONB)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "jsonb"

    def test_timestamptz_type(self, parser):
        sql = "CREATE TABLE t (created_at TIMESTAMPTZ)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "timestamptz"

    def test_bytea_type(self, parser):
        sql = "CREATE TABLE t (blob BYTEA)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        # sqlglot normalizes BYTEA to varbinary
        assert col.type == "varbinary"

    def test_varchar_with_length(self, parser):
        sql = "CREATE TABLE t (name VARCHAR(255))"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.type == "varchar"
        assert col.length == 255


# ── COMMENT ON TABLE ────────────────────────────────────────────────────────────


class TestCommentOnTable:
    def test_comment_on_table(self, parser):
        sql = "CREATE TABLE users (id INT);\nCOMMENT ON TABLE users IS '用户表'"
        result = parser.parse(sql)
        assert result.tables[0].comment == "用户表"

    def test_comment_on_table_no_comment(self, parser):
        sql = "CREATE TABLE users (id INT)"
        result = parser.parse(sql)
        assert result.tables[0].comment == ""

    def test_comment_on_table_before_create(self, parser):
        """COMMENT ON may appear before CREATE TABLE; order shouldn't matter."""
        sql = "COMMENT ON TABLE users IS '用户表';\nCREATE TABLE users (id INT)"
        result = parser.parse(sql)
        assert result.tables[0].comment == "用户表"


# ── COMMENT ON COLUMN ───────────────────────────────────────────────────────────


class TestCommentOnColumn:
    def test_comment_on_column(self, parser):
        sql = (
            "CREATE TABLE users (id INT, name VARCHAR(100));\n"
            "COMMENT ON COLUMN users.name IS '用户名'"
        )
        result = parser.parse(sql)
        cols = result.tables[0].columns
        assert cols[1].comment == "用户名"

    def test_comment_on_column_multiple(self, parser):
        sql = (
            "CREATE TABLE users (id INT, name VARCHAR(100), email VARCHAR(255));\n"
            "COMMENT ON COLUMN users.id IS '主键';\n"
            "COMMENT ON COLUMN users.name IS '用户名';\n"
            "COMMENT ON COLUMN users.email IS '邮箱'"
        )
        result = parser.parse(sql)
        cols = {c.name: c for c in result.tables[0].columns}
        assert cols["id"].comment == "主键"
        assert cols["name"].comment == "用户名"
        assert cols["email"].comment == "邮箱"

    def test_comment_on_column_no_comment(self, parser):
        result = parser.parse("CREATE TABLE t (id INT)")
        col = result.tables[0].columns[0]
        assert col.comment == ""


# ── COMMENT ON with Quoted Names ────────────────────────────────────────────────


class TestCommentOnQuotedNames:
    def test_comment_on_table_quoted(self, parser):
        sql = (
            "CREATE TABLE \"user table\" (id INT);\n"
            "COMMENT ON TABLE \"user table\" IS '用户信息表'"
        )
        result = parser.parse(sql)
        assert result.tables[0].name == "user table"
        assert result.tables[0].comment == "用户信息表"

    def test_comment_on_column_quoted(self, parser):
        sql = (
            'CREATE TABLE t ("user name" VARCHAR(100));\n'
            "COMMENT ON COLUMN t.\"user name\" IS '用户名'"
        )
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.name == "user name"
        assert col.comment == "用户名"


# ── Foreign Keys ────────────────────────────────────────────────────────────────


class TestPostgresForeignKeys:
    def test_column_level_fk(self, parser):
        sql = (
            "CREATE TABLE orders (user_id INT REFERENCES users(id))"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["user_id"]
        assert fks[0].ref_table == "users"
        assert fks[0].ref_columns == ["id"]

    def test_table_level_fk(self, parser):
        sql = (
            "CREATE TABLE orders (\n"
            "  order_id SERIAL PRIMARY KEY,\n"
            "  user_id INT NOT NULL,\n"
            "  FOREIGN KEY (user_id) REFERENCES users(id)\n"
            ")"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["user_id"]
        assert fks[0].ref_table == "users"
        assert fks[0].ref_columns == ["id"]

    def test_constraint_fk(self, parser):
        sql = (
            "CREATE TABLE orders (\n"
            "  order_id SERIAL PRIMARY KEY,\n"
            "  user_id INT NOT NULL,\n"
            "  CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)\n"
            ")"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["user_id"]
        assert fks[0].ref_table == "users"


# ── Composite Primary Key ───────────────────────────────────────────────────────


class TestCompositePrimaryKey:
    def test_composite_pk(self, parser):
        sql = (
            "CREATE TABLE order_items (\n"
            "  order_id INT NOT NULL,\n"
            "  product_id INT NOT NULL,\n"
            "  quantity INT,\n"
            "  PRIMARY KEY (order_id, product_id)\n"
            ")"
        )
        result = parser.parse(sql)
        cols = {c.name: c for c in result.tables[0].columns}
        assert cols["order_id"].primary_key is True
        assert cols["product_id"].primary_key is True
        assert cols["quantity"].primary_key is False


# ── Integration: Realistic PostgreSQL DDL ───────────────────────────────────────


class TestPostgresIntegration:
    def test_realistic_users_table(self, parser):
        sql = (
            "CREATE TABLE users (\n"
            '  "id" SERIAL PRIMARY KEY,\n'
            '  "username" VARCHAR(50) NOT NULL,\n'
            '  "email" VARCHAR(255),\n'
            '  "status" SMALLINT DEFAULT 1,\n'
            '  "created_at" TIMESTAMPTZ DEFAULT NOW()\n'
            ");\n"
            "COMMENT ON TABLE users IS '系统用户表';\n"
            "COMMENT ON COLUMN users.id IS '用户ID';\n"
            "COMMENT ON COLUMN users.username IS '用户名';\n"
            "COMMENT ON COLUMN users.email IS '邮箱';\n"
            "COMMENT ON COLUMN users.status IS '状态 1:启用 0:禁用';\n"
            "COMMENT ON COLUMN users.created_at IS '创建时间'"
        )
        result = parser.parse(sql)
        assert len(result.tables) == 1
        t = result.tables[0]
        assert t.name == "users"
        assert t.comment == "系统用户表"

        cols = {c.name: c for c in t.columns}
        assert cols["id"].type == "integer"
        assert cols["id"].auto_increment is True
        assert cols["id"].primary_key is True
        assert cols["id"].nullable is False
        assert cols["id"].comment == "用户ID"

        assert cols["username"].type == "varchar"
        assert cols["username"].length == 50
        assert cols["username"].nullable is False
        assert cols["username"].comment == "用户名"

        assert cols["email"].type == "varchar"
        assert cols["email"].length == 255
        assert cols["email"].comment == "邮箱"

        assert cols["status"].type == "smallint"
        assert cols["status"].default == "1"
        assert cols["status"].comment == "状态 1:启用 0:禁用"

        assert cols["created_at"].type == "timestamptz"
        assert cols["created_at"].comment == "创建时间"

    def test_realistic_orders_table(self, parser):
        sql = (
            "CREATE TABLE orders (\n"
            '  "id" SERIAL PRIMARY KEY,\n'
            '  "user_id" INT NOT NULL,\n'
            '  "total" DECIMAL(10,2) NOT NULL DEFAULT 0.00,\n'
            '  "status" SMALLINT DEFAULT 0,\n'
            '  "created_at" TIMESTAMPTZ DEFAULT NOW()\n'
            ");\n"
            "COMMENT ON TABLE orders IS '订单表';\n"
            "COMMENT ON COLUMN orders.id IS '订单ID';\n"
            "COMMENT ON COLUMN orders.user_id IS '用户ID';\n"
            "COMMENT ON COLUMN orders.total IS '总金额';\n"
            "COMMENT ON COLUMN orders.status IS '订单状态';\n"
            "COMMENT ON COLUMN orders.created_at IS '创建时间'"
        )
        result = parser.parse(sql)
        t = result.tables[0]
        assert t.name == "orders"
        assert t.comment == "订单表"

        cols = {c.name: c for c in t.columns}
        assert cols["id"].type == "integer"
        assert cols["id"].auto_increment is True

        assert cols["total"].type == "decimal"
        assert cols["total"].length == 10

        assert cols["created_at"].type == "timestamptz"

    def test_uuid_primary_key(self, parser):
        sql = (
            "CREATE TABLE products (\n"
            '  "id" UUID PRIMARY KEY,\n'
            '  "name" VARCHAR(200) NOT NULL,\n'
            '  "metadata" JSONB\n'
            ")"
        )
        result = parser.parse(sql)
        t = result.tables[0]
        assert t.name == "products"
        cols = {c.name: c for c in t.columns}
        assert cols["id"].type == "uuid"
        assert cols["id"].primary_key is True
        assert cols["id"].nullable is False
        assert cols["name"].type == "varchar"
        assert cols["metadata"].type == "jsonb"


# ── Error Resilience ────────────────────────────────────────────────────────────


class TestErrorResilience:
    def test_empty_input(self, parser):
        result = parser.parse("")
        assert result.tables == []
        assert len(result.errors) == 0

    def test_only_comment_on_table(self, parser):
        """COMMENT ON without a matching CREATE TABLE is silently ignored."""
        sql = "COMMENT ON TABLE users IS '用户表'"
        result = parser.parse(sql)
        assert result.tables == []

    def test_invalid_sql_skipped(self, parser):
        sql = (
            "CREATE TABLE t1 (id INT);\n"
            "This is not valid SQL;\n"
            "CREATE TABLE t2 (name TEXT)"
        )
        result = parser.parse(sql)
        assert len(result.tables) == 2
        assert result.tables[0].name == "t1"
        assert result.tables[1].name == "t2"
