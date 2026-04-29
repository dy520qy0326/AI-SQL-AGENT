"""Tests for MySQLParser — MySQL dialect-specific parsing."""

import pytest
from app.parser.mysql import MySQLParser


@pytest.fixture
def parser():
    return MySQLParser()


# ── Dialect ─────────────────────────────────────────────────────────────────────


class TestDialect:
    def test_dialect_is_mysql(self, parser):
        assert parser.dialect == "mysql"

    def test_auto_detect_from_auto_increment(self, parser):
        sql = "CREATE TABLE t (id INT AUTO_INCREMENT)"
        result = parser.parse(sql)
        assert result.dialect == "mysql"

    def test_auto_detect_from_backtick(self, parser):
        sql = "CREATE TABLE `t` (id INT)"
        result = parser.parse(sql)
        assert result.dialect == "mysql"


# ── AUTO_INCREMENT ──────────────────────────────────────────────────────────────


class TestAutoIncrement:
    def test_auto_increment_column(self, parser):
        result = parser.parse("CREATE TABLE t (id INT AUTO_INCREMENT)")
        col = result.tables[0].columns[0]
        assert col.auto_increment is True

    def test_auto_increment_with_primary_key(self, parser):
        sql = "CREATE TABLE t (id INT AUTO_INCREMENT PRIMARY KEY)"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.auto_increment is True
        assert col.primary_key is True
        assert col.nullable is False

    def test_no_auto_increment(self, parser):
        result = parser.parse("CREATE TABLE t (id INT PRIMARY KEY)")
        col = result.tables[0].columns[0]
        assert col.auto_increment is False

    def test_multiple_columns_auto_increment_single(self, parser):
        sql = "CREATE TABLE t (id INT AUTO_INCREMENT, name VARCHAR(100))"
        result = parser.parse(sql)
        cols = result.tables[0].columns
        assert cols[0].auto_increment is True
        assert cols[1].auto_increment is False


# ── Backtick Quoting ───────────────────────────────────────────────────────────


class TestBacktickQuoting:
    def test_backtick_table_name(self, parser):
        result = parser.parse("CREATE TABLE `users` (id INT)")
        assert result.tables[0].name == "users"

    def test_backtick_column_name(self, parser):
        result = parser.parse(
            "CREATE TABLE t (`user-name` VARCHAR(100))"
        )
        col = result.tables[0].columns[0]
        assert col.name == "user-name"

    def test_backtick_schema_table(self, parser):
        result = parser.parse(
            "CREATE TABLE `mydb`.`users` (id INT)"
        )
        t = result.tables[0]
        assert t.name == "users"
        assert t.schema_ == "mydb"


# ── MySQL-Specific Types ────────────────────────────────────────────────────────


class TestMySqlTypes:
    def test_tinyint(self, parser):
        result = parser.parse("CREATE TABLE t (flag TINYINT)")
        col = result.tables[0].columns[0]
        assert col.type == "tinyint"

    def test_smallint(self, parser):
        result = parser.parse("CREATE TABLE t (age SMALLINT)")
        col = result.tables[0].columns[0]
        assert col.type == "smallint"

    def test_bigint(self, parser):
        result = parser.parse("CREATE TABLE t (id BIGINT)")
        col = result.tables[0].columns[0]
        assert col.type == "bigint"

    def test_datetime(self, parser):
        result = parser.parse("CREATE TABLE t (created_at DATETIME)")
        col = result.tables[0].columns[0]
        assert col.type == "datetime"

    def test_timestamp(self, parser):
        result = parser.parse("CREATE TABLE t (ts TIMESTAMP)")
        col = result.tables[0].columns[0]
        # sqlglot normalizes TIMESTAMP to TIMESTAMPTZ internally
        assert col.type == "timestamptz"

    def test_varchar_with_length(self, parser):
        result = parser.parse(
            "CREATE TABLE t (name VARCHAR(255))"
        )
        col = result.tables[0].columns[0]
        assert col.type == "varchar"
        assert col.length == 255

    def test_bigint_with_length(self, parser):
        result = parser.parse(
            "CREATE TABLE t (id BIGINT(20))"
        )
        col = result.tables[0].columns[0]
        assert col.type == "bigint"


# ── Table Options (ignored, not errors) ─────────────────────────────────────────


class TestTableOptions:
    def test_engine_option(self, parser):
        sql = "CREATE TABLE t (id INT) ENGINE=InnoDB"
        result = parser.parse(sql)
        assert len(result.tables) == 1
        assert result.tables[0].name == "t"
        assert result.errors == []

    def test_engine_and_charset(self, parser):
        sql = "CREATE TABLE t (id INT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        result = parser.parse(sql)
        assert len(result.tables) == 1
        assert result.errors == []

    def test_full_table_options(self, parser):
        sql = (
            "CREATE TABLE t ("
            "  id INT AUTO_INCREMENT PRIMARY KEY,"
            "  name VARCHAR(100)"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        )
        result = parser.parse(sql)
        assert len(result.tables) == 1
        col = result.tables[0].columns[0]
        assert col.auto_increment is True
        assert col.primary_key is True
        assert result.errors == []

    def test_auto_increment_offset_option(self, parser):
        sql = "CREATE TABLE t (id INT) ENGINE=InnoDB AUTO_INCREMENT=100"
        result = parser.parse(sql)
        assert len(result.tables) == 1
        assert result.errors == []


# ── Column COMMENT ──────────────────────────────────────────────────────────────


class TestColumnComment:
    def test_column_comment(self, parser):
        sql = "CREATE TABLE t (name VARCHAR(100) COMMENT '用户名')"
        result = parser.parse(sql)
        col = result.tables[0].columns[0]
        assert col.comment == "用户名"

    def test_multiple_column_comments(self, parser):
        sql = (
            "CREATE TABLE t ("
            "  id INT AUTO_INCREMENT COMMENT '主键',"
            "  name VARCHAR(100) NOT NULL COMMENT '姓名',"
            "  email VARCHAR(255) COMMENT '邮箱'"
            ")"
        )
        result = parser.parse(sql)
        cols = result.tables[0].columns
        assert cols[0].comment == "主键"
        assert cols[1].comment == "姓名"
        assert cols[2].comment == "邮箱"

    def test_column_without_comment(self, parser):
        result = parser.parse("CREATE TABLE t (id INT)")
        col = result.tables[0].columns[0]
        assert col.comment == ""


# ── Table-Level COMMENT ─────────────────────────────────────────────────────────


class TestTableComment:
    def test_table_comment(self, parser):
        sql = "CREATE TABLE t (id INT) COMMENT='用户表'"
        result = parser.parse(sql)
        assert result.tables[0].comment == "用户表"

    def test_table_comment_with_engine(self, parser):
        sql = "CREATE TABLE t (id INT) ENGINE=InnoDB COMMENT='订单表'"
        result = parser.parse(sql)
        assert result.tables[0].comment == "订单表"

    def test_table_comment_no_comment(self, parser):
        sql = "CREATE TABLE t (id INT) ENGINE=InnoDB"
        result = parser.parse(sql)
        assert result.tables[0].comment == ""

    def test_table_comment_with_backtick(self, parser):
        sql = "CREATE TABLE `orders` (id INT) ENGINE=InnoDB COMMENT='订单表'"
        result = parser.parse(sql)
        assert result.tables[0].name == "orders"
        assert result.tables[0].comment == "订单表"

    def test_table_comment_all_features(self, parser):
        """Integration: table with all MySQL features combined."""
        sql = (
            "CREATE TABLE `users` (\n"
            "  id INT AUTO_INCREMENT COMMENT '主键',\n"
            "  `user-name` VARCHAR(50) NOT NULL COMMENT '用户名',\n"
            "  email VARCHAR(100) COMMENT '邮箱',\n"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表'"
        )
        result = parser.parse(sql)
        assert len(result.tables) == 1
        t = result.tables[0]
        assert t.name == "users"
        assert t.comment == "用户信息表"
        cols = {c.name: c for c in t.columns}
        assert cols["id"].auto_increment is True
        assert cols["id"].comment == "主键"
        assert cols["user-name"].nullable is False
        assert cols["user-name"].comment == "用户名"
        assert cols["email"].comment == "邮箱"
        assert cols["created_at"].type == "datetime"
        assert result.errors == []


# ── Foreign Key with MySQL syntax ───────────────────────────────────────────────


class TestMySqlForeignKeys:
    def test_column_level_fk(self, parser):
        sql = "CREATE TABLE t (user_id INT REFERENCES `users`(`id`))"
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["user_id"]
        assert fks[0].ref_table == "users"
        assert fks[0].ref_columns == ["id"]

    def test_table_level_fk(self, parser):
        sql = (
            "CREATE TABLE `orders` (\n"
            "  order_id INT AUTO_INCREMENT PRIMARY KEY,\n"
            "  user_id INT NOT NULL,\n"
            "  FOREIGN KEY (user_id) REFERENCES `users`(`id`)\n"
            ") ENGINE=InnoDB"
        )
        result = parser.parse(sql)
        fks = result.tables[0].foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["user_id"]
        assert fks[0].ref_table == "users"
        assert fks[0].ref_columns == ["id"]


# ── Integration: Realistic MySQL DDL ────────────────────────────────────────────


class TestMySqlIntegration:
    def test_realistic_users_table(self, parser):
        sql = (
            "CREATE TABLE `sys_users` (\n"
            "  `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '用户ID',\n"
            "  `username` VARCHAR(50) NOT NULL COMMENT '用户名',\n"
            "  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',\n"
            "  `status` TINYINT(4) DEFAULT 1 COMMENT '状态 1:启用 0:禁用',\n"
            "  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',\n"
            "  PRIMARY KEY (`id`),\n"
            "  UNIQUE KEY `uk_username` (`username`),\n"
            "  KEY `idx_email` (`email`)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表'"
        )
        result = parser.parse(sql)
        assert len(result.tables) == 1
        t = result.tables[0]
        assert t.name == "sys_users"
        assert t.comment == "系统用户表"

        cols = {c.name: c for c in t.columns}
        assert cols["id"].type == "bigint"
        assert cols["id"].length == 20
        assert cols["id"].nullable is False
        assert cols["id"].auto_increment is True
        assert cols["id"].primary_key is True
        assert cols["id"].comment == "用户ID"

        assert cols["username"].type == "varchar"
        assert cols["username"].length == 50
        assert cols["username"].nullable is False
        assert cols["username"].comment == "用户名"

        assert cols["email"].nullable is True
        assert cols["email"].default == "NULL"
        assert cols["email"].comment == "邮箱"

        assert cols["status"].type == "tinyint"
        assert cols["status"].length == 4
        assert cols["status"].default == "1"
        assert cols["status"].comment == "状态 1:启用 0:禁用"

        assert cols["created_at"].type == "datetime"

    def test_realistic_orders_table(self, parser):
        sql = (
            "CREATE TABLE `sys_orders` (\n"
            "  `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '订单ID',\n"
            "  `user_id` BIGINT(20) NOT NULL COMMENT '用户ID',\n"
            "  `amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '金额',\n"
            "  `status` TINYINT(4) DEFAULT 0 COMMENT '订单状态',\n"
            "  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',\n"
            "  PRIMARY KEY (`id`),\n"
            "  KEY `idx_user_id` (`user_id`),\n"
            "  KEY `idx_created_at` (`created_at`),\n"
            "  CONSTRAINT `fk_user_id` FOREIGN KEY (`user_id`) REFERENCES `sys_users` (`id`)\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表'"
        )
        result = parser.parse(sql)
        assert len(result.tables) == 1
        t = result.tables[0]
        assert t.name == "sys_orders"
        assert t.comment == "订单表"

        cols = {c.name: c for c in t.columns}
        assert cols["amount"].type == "decimal"
        assert cols["amount"].length == 10

        fks = t.foreign_keys
        assert len(fks) == 1
        assert fks[0].columns == ["user_id"]
        assert fks[0].ref_table == "sys_users"
        assert fks[0].ref_columns == ["id"]

    def test_indexes_not_implemented_yet(self, parser):
        """Verify indexes are not yet extracted (index parse is a later task)."""
        sql = "CREATE TABLE t (id INT, INDEX idx_id (id))"
        result = parser.parse(sql)
        # Index parsing is not in scope for base parser currently
        # This just confirms it doesn't crash
        assert len(result.tables) == 1
