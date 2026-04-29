"""Tests for NL Query context construction strategy."""

import pytest
import pytest_asyncio

from app.nl.context import (
    _search_mode,
    _summary_mode,
    build_context,
)
from app.parser.models import ParseResult
from app.store.repository import Repository


@pytest_asyncio.fixture
async def populated_project(async_session):
    """Create a project with sample tables and relations for context tests."""
    from app.parser.models import Column, ForeignKey, Index, Table

    async with async_session.begin():
        repo = Repository(async_session)
        p = await repo.create_project("ctx-proj", None, "mysql")
        pr = ParseResult(
            dialect="mysql",
            tables=[
                Table(
                    name="users", schema="", comment="用户表",
                    columns=[
                        Column(name="id", type="int", primary_key=True, comment="用户ID"),
                        Column(name="name", type="varchar", nullable=False),
                        Column(name="email", type="varchar"),
                    ],
                    indexes=[Index(name="idx_email", unique=True, columns=["email"])],
                    foreign_keys=[],
                ),
                Table(
                    name="orders", schema="", comment="订单表",
                    columns=[
                        Column(name="id", type="int", primary_key=True),
                        Column(name="user_id", type="int", nullable=False),
                        Column(name="total", type="decimal"),
                        Column(name="deleted_at", type="timestamp"),
                    ],
                    indexes=[],
                    foreign_keys=[
                        ForeignKey(columns=["user_id"], ref_table="users", ref_columns=["id"]),
                    ],
                ),
                Table(
                    name="products", schema="", comment="",
                    columns=[
                        Column(name="id", type="int", primary_key=True),
                        Column(name="name", type="varchar", nullable=False),
                        Column(name="price", type="decimal"),
                    ],
                    indexes=[],
                    foreign_keys=[],
                ),
            ],
            errors=[],
        )
        tables = await repo.save_parse_result(p.id, pr)

        from app.store.repository import RelationData

        await repo.save_relations(p.id, [
            RelationData(
                source_table_id=tables[1].id,
                source_columns=["user_id"],
                target_table_id=tables[0].id,
                target_columns=["id"],
                relation_type="FOREIGN_KEY",
                confidence=1.0,
                source="FK",
            ),
        ])

    return p.id


class TestContextModes:
    @pytest.mark.asyncio
    async def test_single_table_mode(self, async_session, populated_project):
        project_id = populated_project
        ctx = await build_context(async_session, project_id, "orders 表有哪些字段")
        assert ctx.mode == "single"
        assert "orders" in ctx.candidate_tables
        assert "orders" in ctx.system_prompt
        assert "users" in ctx.system_prompt

    @pytest.mark.asyncio
    async def test_cross_table_relation_mode(self, async_session, populated_project):
        project_id = populated_project
        ctx = await build_context(async_session, project_id, "users 和 orders 怎么关联")
        assert ctx.mode == "relation"
        assert "users" in ctx.candidate_tables
        assert "orders" in ctx.candidate_tables

    @pytest.mark.asyncio
    async def test_fuzzy_mode_when_no_match(self, async_session, populated_project):
        project_id = populated_project
        ctx = await build_context(async_session, project_id, "这个数据库做什么的")
        assert ctx.mode == "fuzzy"
        assert ctx.candidate_tables == []

    @pytest.mark.asyncio
    async def test_search_mode_with_column_keyword(self, async_session, populated_project):
        project_id = populated_project
        ctx = await build_context(async_session, project_id, "哪些表有 deleted_at 字段")
        assert ctx.mode == "search"

    @pytest.mark.asyncio
    async def test_empty_project(self, async_session):
        repo = Repository(async_session)
        async with async_session.begin():
            p = await repo.create_project("empty-proj", None, "mysql")
            ctx = await build_context(async_session, p.id, "what tables exist")
            assert ctx.mode == "fuzzy"
            assert ctx.token_estimate > 0

    @pytest.mark.asyncio
    async def test_context_includes_token_estimate(self, async_session, populated_project):
        project_id = populated_project
        ctx = await build_context(async_session, project_id, "orders 有哪些字段")
        assert ctx.token_estimate > 0
        assert isinstance(ctx.token_estimate, int)


class TestBuildSchemaText:
    def test_summary_mode_shows_table_overview(self):
        tables = [
            _make_orm_table("users", [("id", "int", True), ("name", "varchar")]),
            _make_orm_table("orders", [("id", "int", True), ("user_id", "int")]),
        ]
        text = _summary_mode(tables, max_tables=30)
        assert "users" in text
        assert "orders" in text
        assert "PK=" in text

    def test_search_mode_shows_index(self):
        tables = [
            _make_orm_table("users", [("id", "int", True), ("email", "varchar")]),
            _make_orm_table("orders", [("id", "int", True), ("user_id", "int")]),
        ]
        all_columns = {"email": [("users", "email")]}
        text = _search_mode(tables, {"email"}, all_columns)
        assert "users" in text
        assert "orders" in text
        assert "email" in text
        assert "Matched Columns" in text


class TestHistoryInjection:
    @pytest.mark.asyncio
    async def test_history_injected_with_session(self, async_session, populated_project):
        project_id = populated_project
        repo = Repository(async_session)
        async with async_session.begin():
            session = await repo.create_session(project_id, title="test")
            await repo.add_message(session.id, "user", "tell me about orders")
            await repo.add_message(session.id, "assistant", "orders has id, user_id, total")

        ctx = await build_context(async_session, project_id, "它的字段有哪些", session.id)
        assert "tell me about orders" in ctx.user_message
        assert "Previous conversation" in ctx.user_message
        assert "它的字段有哪些" in ctx.user_message


# ── Helpers ──

from app.db.models import (
    Column as ColumnModel,
    Index as IndexModel,
    Table,
)


def _make_orm_table(name, cols):
    """Create a minimal SQLAlchemy Table model for use in context tests."""
    t = Table(name=name, schema_name="", comment="")
    t.id = f"id-{name}"
    t.columns = []
    for cname, ctype, *rest in cols:
        is_pk = rest[0] if rest else False
        c = ColumnModel(name=cname, data_type=ctype, is_primary_key=is_pk, nullable=True, comment="")
        c.name = cname
        t.columns.append(c)
    t.indexes = []
    t.foreign_keys = []
    return t
