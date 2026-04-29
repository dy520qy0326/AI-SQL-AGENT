import pytest
from app.db.models import Project, Table, Column, Index, ForeignKeyModel, Relation
from app.store.repository import Repository, RelationData
from app.parser.models import ParseResult


@pytest.mark.asyncio
async def test_create_and_get_project(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("test-proj", "desc", "mysql")
        assert p.id is not None
        assert p.name == "test-proj"
        assert p.dialect == "mysql"

        info = await repo.get_project(p.id)
        assert info is not None
        assert info["name"] == "test-proj"
        assert info["table_count"] == 0
        assert info["relation_count"] == 0


@pytest.mark.asyncio
async def test_list_projects(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        await repo.create_project("proj-a", None, "mysql")
        await repo.create_project("proj-b", None, "postgresql")

        items, total = await repo.list_projects(page=1, size=10)
        assert total >= 2


@pytest.mark.asyncio
async def test_delete_project_cascade(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("to-delete", None, "mysql")

        # Save a simple parse result
        pr = ParseResult(dialect="mysql", tables=[
            _make_table("t1", [("id", "int")]),
        ], errors=[])
        await repo.save_parse_result(p.id, pr)

        # Verify tables exist
        tables = await repo.get_tables(p.id)
        assert len(tables) == 1

        # Delete project
        deleted = await repo.delete_project(p.id)
        assert deleted is True

        # Verify cascade
        info = await repo.get_project(p.id)
        assert info is None


@pytest.mark.asyncio
async def test_save_parse_result(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("parse-test", None, "mysql")
        pr = ParseResult(
            dialect="mysql",
            tables=[
                _make_table("users", [
                    ("id", "int", True, False),
                    ("name", "varchar"),
                    ("email", "varchar"),
                ], indexes=[
                    ("idx_email", True, ["email"]),
                ], foreign_keys=[]),
                _make_table("orders", [
                    ("id", "int", True, False),
                    ("user_id", "int"),
                    ("total", "decimal"),
                ], indexes=[], foreign_keys=[
                    (["user_id"], "users", ["id"]),
                ]),
            ],
            errors=[],
        )
        tables = await repo.save_parse_result(p.id, pr)
        assert len(tables) == 2

        # Verify tables are persisted
        saved = await repo.get_tables(p.id)
        assert len(saved) == 2
        assert {t.name for t in saved} == {"users", "orders"}


@pytest.mark.asyncio
async def test_get_table_detail(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("detail-test", None, "mysql")
        pr = ParseResult(dialect="mysql", tables=[
            _make_table("products", [
                ("id", "int", False, True),
                ("name", "varchar"),
                ("price", "decimal"),
            ]),
        ], errors=[])
        tables = await repo.save_parse_result(p.id, pr)

        detail = await repo.get_table_detail(tables[0].id)
        assert detail is not None
        assert detail.name == "products"
        assert len(detail.columns) == 3
        assert detail.columns[0].is_primary_key is True


@pytest.mark.asyncio
async def test_save_and_get_relations(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("rel-test", None, "mysql")
        pr = ParseResult(dialect="mysql", tables=[
            _make_table("users", [("id", "int", True, False)]),
            _make_table("orders", [("id", "int", True, False), ("user_id", "int")]),
        ], errors=[])
        tables = await repo.save_parse_result(p.id, pr)

        rels = [
            RelationData(
                source_table_id=tables[1].id,
                source_columns=["user_id"],
                target_table_id=tables[0].id,
                target_columns=["id"],
                relation_type="FOREIGN_KEY",
                confidence=1.0,
                source="test FK",
            )
        ]
        await repo.save_relations(p.id, rels)
        saved = await repo.get_relations(p.id)
        assert len(saved) == 1
        assert saved[0].relation_type == "FOREIGN_KEY"
        assert saved[0].confidence == 1.0


@pytest.mark.asyncio
async def test_get_relations_filtered(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("filter-test", None, "mysql")
        pr = ParseResult(dialect="mysql", tables=[
            _make_table("a", [("id", "int", True, False)]),
            _make_table("b", [("id", "int", True, False), ("a_id", "int")]),
            _make_table("c", [("id", "int", True, False)]),
        ], errors=[])
        tables = await repo.save_parse_result(p.id, pr)

        rels = [
            RelationData(tables[1].id, ["a_id"], tables[0].id, ["id"], "FOREIGN_KEY", 1.0),
            RelationData(tables[2].id, ["id"], tables[0].id, ["id"], "INFERRED", 0.60),
        ]
        await repo.save_relations(p.id, rels)

        all_rels = await repo.get_relations(p.id)
        assert len(all_rels) == 2

        fk_only = await repo.get_relations(p.id, type_filter="FOREIGN_KEY")
        assert len(fk_only) == 1

        high_conf = await repo.get_relations(p.id, min_confidence=0.8)
        assert len(high_conf) == 1


@pytest.mark.asyncio
async def test_get_project_tables_dict(async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("dict-test", None, "mysql")
        pr = ParseResult(dialect="mysql", tables=[
            _make_table("Users", [("id", "int")]),
            _make_table("ORDERS", [("id", "int")]),
        ], errors=[])
        await repo.save_parse_result(p.id, pr)

        d = await repo.get_project_tables_dict(p.id)
        assert "users" in d
        assert "orders" in d


# ── Helpers ──

from app.parser.models import Table as PTable, Column as PColumn, Index as PIndex, ForeignKey as PFk


def _make_table(name, cols, indexes=None, foreign_keys=None):
    return PTable(
        name=name,
        schema="",
        comment="",
        columns=[PColumn(
            name=c[0], type=c[1],
            nullable=c[2] if len(c) > 2 else True,
            primary_key=c[3] if len(c) > 3 else False,
        ) for c in cols],
        indexes=[PIndex(name=idx[0], unique=idx[1], columns=idx[2]) for idx in (indexes or [])],
        foreign_keys=[PFk(columns=fk[0], ref_table=fk[1], ref_columns=fk[2]) for fk in (foreign_keys or [])],
    )
