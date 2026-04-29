"""PostgreSQL parser integration test — pagila-style DDL sample.

Based on common PostgreSQL schema patterns.
Verifies all tables are correctly parsed with PG-specific types.
"""

import pytest
from app.parser.postgres import PostgreSQLParser

# ── Sample DDL ────────────────────────────────────────────────────────────────
# A PostgreSQL schema with 8 tables covering SERIAL, UUID, JSONB, TIMESTAMPTZ,
# BYTEA, composite keys, foreign keys, and COMMENT ON statements.

SAMPLE_DDL = """
CREATE TABLE users (
    id              SERIAL          PRIMARY KEY,
    username        VARCHAR(50)     NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    bio             TEXT,
    preferences     JSONB           DEFAULT '{}',
    is_active       BOOLEAN         DEFAULT true,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

CREATE TABLE categories (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    description     TEXT,
    parent_id       INT             REFERENCES categories(id),
    sort_order      INT             DEFAULT 0
);

CREATE TABLE posts (
    id              SERIAL          PRIMARY KEY,
    title           VARCHAR(200)    NOT NULL,
    content         TEXT            NOT NULL,
    author_id       INT             NOT NULL,
    category_id     INT             NOT NULL,
    metadata        JSONB,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    FOREIGN KEY (author_id) REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE comments (
    id              SERIAL          PRIMARY KEY,
    post_id         INT             NOT NULL,
    author_id       INT             NOT NULL,
    body            TEXT            NOT NULL,
    moderated       BOOLEAN         DEFAULT false,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE tags (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(50)     NOT NULL,
    slug            VARCHAR(50)     NOT NULL
);

CREATE TABLE post_tags (
    post_id         INT             NOT NULL,
    tag_id          INT             NOT NULL,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE audit_log (
    id              UUID            PRIMARY KEY,
    entity_type     VARCHAR(50)     NOT NULL,
    entity_id       INT             NOT NULL,
    action          VARCHAR(50)     NOT NULL,
    changes         JSONB,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE user_sessions (
    id              UUID            PRIMARY KEY,
    user_id         INT             NOT NULL,
    token_hash      VARCHAR(64)     NOT NULL,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    session_data    BYTEA,
    expires_at      TIMESTAMPTZ     NOT NULL,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

COMMENT ON TABLE users IS '系统用户表';
COMMENT ON TABLE posts IS '文章表';
COMMENT ON TABLE comments IS '评论表';
COMMENT ON TABLE audit_log IS '审计日志表';

COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users.email IS '电子邮箱';
COMMENT ON COLUMN users.preferences IS '用户偏好设置(JSON)';
COMMENT ON COLUMN posts.title IS '文章标题';
COMMENT ON COLUMN posts.content IS '文章正文';
COMMENT ON COLUMN audit_log.changes IS '变更内容(JSON)';
"""


@pytest.fixture(scope="module")
def sample_result():
    parser = PostgreSQLParser()
    return parser.parse(SAMPLE_DDL)


# ── Test data ─────────────────────────────────────────────────────────────────

TABLE_EXPECTATIONS = [
    (
        "users", 8, 0,
        {
            "id": {"type": "integer", "nullable": False, "primary_key": True, "auto_increment": True},
            "username": {"type": "varchar", "length": 50, "nullable": False},
            "email": {"type": "varchar", "length": 255, "nullable": False},
            "bio": {"type": "text", "nullable": True},
            "preferences": {"type": "jsonb", "nullable": True, "default": "{}"},
            "is_active": {"type": "boolean", "nullable": True, "default": "true"},
            "created_at": {"type": "timestamptz", "nullable": True},
            "updated_at": {"type": "timestamptz", "nullable": True},
        },
    ),
    (
        "categories", 5, 1,
        {
            "id": {"type": "integer", "nullable": False, "primary_key": True, "auto_increment": True},
            "name": {"type": "varchar", "length": 100, "nullable": False},
            "description": {"type": "text", "nullable": True},
            "parent_id": {"type": "int", "nullable": True},
            "sort_order": {"type": "int", "nullable": True, "default": "0"},
        },
    ),
    (
        "posts", 8, 2,
        {
            "id": {"type": "integer", "nullable": False, "primary_key": True, "auto_increment": True},
            "title": {"type": "varchar", "length": 200, "nullable": False},
            "content": {"type": "text", "nullable": False},
            "author_id": {"type": "int", "nullable": False},
            "category_id": {"type": "int", "nullable": False},
            "metadata": {"type": "jsonb", "nullable": True},
            "published_at": {"type": "timestamptz", "nullable": True},
            "created_at": {"type": "timestamptz", "nullable": True, "default": "CURRENT_TIMESTAMP()"},
        },
    ),
    (
        "comments", 6, 2,
        {
            "id": {"type": "integer", "nullable": False, "primary_key": True, "auto_increment": True},
            "post_id": {"type": "int", "nullable": False},
            "author_id": {"type": "int", "nullable": False},
            "body": {"type": "text", "nullable": False},
            "moderated": {"type": "boolean", "nullable": True, "default": "false"},
            "created_at": {"type": "timestamptz", "nullable": True, "default": "CURRENT_TIMESTAMP()"},
        },
    ),
    (
        "tags", 3, 0,
        {
            "id": {"type": "integer", "nullable": False, "primary_key": True, "auto_increment": True},
            "name": {"type": "varchar", "length": 50, "nullable": False},
            "slug": {"type": "varchar", "length": 50, "nullable": False},
        },
    ),
    (
        "post_tags", 3, 2,
        {
            "post_id": {"type": "int", "nullable": False, "primary_key": True},
            "tag_id": {"type": "int", "nullable": False, "primary_key": True},
            "created_at": {"type": "timestamptz", "nullable": True, "default": "CURRENT_TIMESTAMP()"},
        },
    ),
    (
        "audit_log", 7, 0,
        {
            "id": {"type": "uuid", "nullable": False, "primary_key": True},
            "entity_type": {"type": "varchar", "length": 50, "nullable": False},
            "entity_id": {"type": "int", "nullable": False},
            "action": {"type": "varchar", "length": 50, "nullable": False},
            "changes": {"type": "jsonb", "nullable": True},
            "ip_address": {"type": "varchar", "length": 45, "nullable": True},
            "created_at": {"type": "timestamptz", "nullable": False, "default": "CURRENT_TIMESTAMP()"},
        },
    ),
    (
        "user_sessions", 8, 1,
        {
            "id": {"type": "uuid", "nullable": False, "primary_key": True},
            "user_id": {"type": "int", "nullable": False},
            "token_hash": {"type": "varchar", "length": 64, "nullable": False},
            "ip_address": {"type": "varchar", "length": 45, "nullable": True},
            "user_agent": {"type": "text", "nullable": True},
            "session_data": {"type": "varbinary", "nullable": True},
            "expires_at": {"type": "timestamptz", "nullable": False},
            "created_at": {"type": "timestamptz", "nullable": True, "default": "CURRENT_TIMESTAMP()"},
        },
    ),
]

FK_EXPECTATIONS = {
    "categories": [
        {"columns": ["parent_id"], "ref_table": "categories", "ref_columns": ["id"]},
    ],
    "posts": [
        {"columns": ["author_id"], "ref_table": "users", "ref_columns": ["id"]},
        {"columns": ["category_id"], "ref_table": "categories", "ref_columns": ["id"]},
    ],
    "comments": [
        {"columns": ["post_id"], "ref_table": "posts", "ref_columns": ["id"]},
        {"columns": ["author_id"], "ref_table": "users", "ref_columns": ["id"]},
    ],
    "post_tags": [
        {"columns": ["post_id"], "ref_table": "posts", "ref_columns": ["id"]},
        {"columns": ["tag_id"], "ref_table": "tags", "ref_columns": ["id"]},
    ],
    "user_sessions": [
        {"columns": ["user_id"], "ref_table": "users", "ref_columns": ["id"]},
    ],
}

COMMENT_EXPECTATIONS = {
    "users": "系统用户表",
    "posts": "文章表",
    "comments": "评论表",
    "audit_log": "审计日志表",
}

COLUMN_COMMENT_EXPECTATIONS = {
    "users": {
        "username": "用户名",
        "email": "电子邮箱",
        "preferences": "用户偏好设置(JSON)",
    },
    "posts": {
        "title": "文章标题",
        "content": "文章正文",
    },
    "audit_log": {
        "changes": "变更内容(JSON)",
    },
}


# ── Table Count ────────────────────────────────────────────────────────────────


class TestTableCount:
    def test_exactly_8_tables(self, sample_result):
        assert len(sample_result.tables) == 8

    def test_no_errors(self, sample_result):
        assert sample_result.errors == []


# ── Dialect ────────────────────────────────────────────────────────────────────


class TestDialect:
    def test_dialect_is_postgresql(self, sample_result):
        assert sample_result.dialect == "postgresql"


# ── Parameterized Table Tests ─────────────────────────────────────────────────


class TestTableStructure:
    @pytest.mark.parametrize(
        "name,col_count,fk_count,expected_cols",
        TABLE_EXPECTATIONS,
        ids=[e[0] for e in TABLE_EXPECTATIONS],
    )
    def test_table_metadata(
        self, sample_result, name, col_count, fk_count, expected_cols
    ):
        tables = {t.name: t for t in sample_result.tables}
        assert name in tables, f"Table '{name}' not found"
        table = tables[name]
        assert len(table.columns) == col_count
        assert len(table.foreign_keys) == fk_count

    @pytest.mark.parametrize(
        "name,col_count,fk_count,expected_cols",
        TABLE_EXPECTATIONS,
        ids=[e[0] for e in TABLE_EXPECTATIONS],
    )
    def test_column_types_and_constraints(
        self, sample_result, name, col_count, fk_count, expected_cols
    ):
        tables = {t.name: t for t in sample_result.tables}
        cols = {c.name: c for c in tables[name].columns}

        for col_name, expected in expected_cols.items():
            assert col_name in cols, f"Column '{col_name}' missing in {name}"
            col = cols[col_name]
            for attr, value in expected.items():
                actual = getattr(col, attr)
                assert actual == value, (
                    f"{name}.{col_name}.{attr}: expected {value!r}, got {actual!r}"
                )

    @pytest.mark.parametrize(
        "table_name,expected_fks",
        [(k, v) for k, v in FK_EXPECTATIONS.items()],
        ids=list(FK_EXPECTATIONS.keys()),
    )
    def test_foreign_keys(self, sample_result, table_name, expected_fks):
        tables = {t.name: t for t in sample_result.tables}
        table = tables[table_name]
        assert len(table.foreign_keys) == len(expected_fks)

        for actual, expected in zip(table.foreign_keys, expected_fks):
            assert actual.columns == expected["columns"]
            assert actual.ref_table == expected["ref_table"]
            assert actual.ref_columns == expected["ref_columns"]


# ── SERIAL Type Mapping ───────────────────────────────────────────────────────


class TestSerialMapping:
    @pytest.mark.parametrize(
        "table_name,col_name",
        [
            ("users", "id"),
            ("categories", "id"),
            ("posts", "id"),
            ("comments", "id"),
            ("tags", "id"),
        ],
    )
    def test_serial_is_auto_increment_integer(self, sample_result, table_name, col_name):
        tables = {t.name: t for t in sample_result.tables}
        col = {c.name: c for c in tables[table_name].columns}[col_name]
        assert col.type == "integer"
        assert col.auto_increment is True


# ── PG-Specific Types ─────────────────────────────────────────────────────────


class TestPGTypes:
    def test_uuid_type(self, sample_result):
        tables = {t.name: t for t in sample_result.tables}
        col = {c.name: c for c in tables["audit_log"].columns}["id"]
        assert col.type == "uuid"

    def test_jsonb_type(self, sample_result):
        tables = {t.name: t for t in sample_result.tables}
        for tbl, col_name in [("users", "preferences"), ("posts", "metadata"), ("audit_log", "changes")]:
            col = {c.name: c for c in tables[tbl].columns}[col_name]
            assert col.type == "jsonb", f"{tbl}.{col_name} expected jsonb, got {col.type}"

    def test_timestamptz_type(self, sample_result):
        tables = {t.name: t for t in sample_result.tables}
        for tbl, col_name in [("users", "created_at"), ("posts", "published_at"), ("audit_log", "created_at")]:
            col = {c.name: c for c in tables[tbl].columns}[col_name]
            assert col.type == "timestamptz", f"{tbl}.{col_name} expected timestamptz, got {col.type}"

    def test_bytea_type(self, sample_result):
        tables = {t.name: t for t in sample_result.tables}
        col = {c.name: c for c in tables["user_sessions"].columns}["session_data"]
        # sqlglot normalizes BYTEA to varbinary
        assert col.type == "varbinary"


# ── COMMENT ON ────────────────────────────────────────────────────────────────


class TestComments:
    @pytest.mark.parametrize(
        "table_name,expected_comment",
        [(k, v) for k, v in COMMENT_EXPECTATIONS.items()],
        ids=list(COMMENT_EXPECTATIONS.keys()),
    )
    def test_table_comments(self, sample_result, table_name, expected_comment):
        tables = {t.name: t for t in sample_result.tables}
        assert tables[table_name].comment == expected_comment

    @pytest.mark.parametrize(
        "table_name,col_name,expected_comment",
        [
            (tn, cn, cv)
            for tn, cols in COLUMN_COMMENT_EXPECTATIONS.items()
            for cn, cv in cols.items()
        ],
        ids=[f"{tn}.{cn}" for tn, cols in COLUMN_COMMENT_EXPECTATIONS.items() for cn in cols],
    )
    def test_column_comments(self, sample_result, table_name, col_name, expected_comment):
        tables = {t.name: t for t in sample_result.tables}
        col = {c.name: c for c in tables[table_name].columns}[col_name]
        assert col.comment == expected_comment

    def test_table_without_comment(self, sample_result):
        tables = {t.name: t for t in sample_result.tables}
        for name in ["categories", "tags", "post_tags", "user_sessions"]:
            assert tables[name].comment == ""


# ── Composite Primary Key ─────────────────────────────────────────────────────


class TestCompositePK:
    def test_post_tags_composite_pk(self, sample_result):
        tables = {t.name: t for t in sample_result.tables}
        cols = {c.name: c for c in tables["post_tags"].columns}
        assert cols["post_id"].primary_key is True
        assert cols["tag_id"].primary_key is True


# ── Performance ────────────────────────────────────────────────────────────────


class TestPerformance:
    def test_parsing_under_500ms(self):
        """500 lines of PG DDL should parse in under 500ms."""
        many_ddls = "\n\n".join([SAMPLE_DDL] * 20)
        line_count = many_ddls.count("\n") + 1
        assert line_count > 500, f"Only {line_count} lines, need > 500"

        import time
        parser = PostgreSQLParser()
        start = time.perf_counter()
        result = parser.parse(many_ddls)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"Parsing {line_count} lines took {elapsed:.1f}ms"
        assert len(result.tables) > 0
        assert result.errors == []
