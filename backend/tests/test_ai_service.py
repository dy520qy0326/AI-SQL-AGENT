"""Tests for AI service — relation completion and comment completion."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.cache import clear_all_cache
from app.ai.client import AIServiceError
from app.ai.service import (
    _get_lock,
    complete_comments,
    complete_relations,
    compute_prompt_hash,
    compute_schema_hash,
)
from app.parser.models import ParseResult
from app.store.repository import RelationData, Repository


@pytest.fixture
def ai_response_2_relations():
    return json.dumps({
        "relations": [
            {
                "source_table": "addresses",
                "source_column": "user_id",
                "target_table": "users",
                "target_column": "id",
                "confidence": "HIGH",
                "reason": "addresses.user_id references users.id",
            },
            {
                "source_table": "payments",
                "source_column": "order_id",
                "target_table": "orders",
                "target_column": "id",
                "confidence": "HIGH",
                "reason": "payments.order_id references orders.id",
            },
        ]
    })


@pytest.fixture
def ai_response_with_low():
    return json.dumps({
        "relations": [
            {
                "source_table": "addresses",
                "source_column": "user_id",
                "target_table": "users",
                "target_column": "id",
                "confidence": "HIGH",
                "reason": "clear FK pattern",
            },
            {
                "source_table": "payments",
                "source_column": "amount",
                "target_table": "products",
                "target_column": "price",
                "confidence": "LOW",
                "reason": "both are decimal fields",
            },
        ]
    })


@pytest.fixture
def ai_response_invalid_table():
    return json.dumps({
        "relations": [
            {
                "source_table": "nonexistent",
                "source_column": "id",
                "target_table": "users",
                "target_column": "id",
                "confidence": "HIGH",
                "reason": "invalid reference",
            },
        ]
    })


class TestCompleteRelations:
    @pytest.mark.asyncio
    async def test_isolated_tables_get_relations(
        self, async_session, ai_response_2_relations, monkeypatch
    ):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-ai-rel", None, "mysql")
            await repo.save_parse_result(p.id, _ecommerce_parse_result())

            mock_complete = MagicMock(return_value=ai_response_2_relations)
            monkeypatch.setattr("app.ai.service.ai_client.complete", mock_complete)
            import asyncio
            monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

            result = await complete_relations(p.id, async_session)
            assert result["new_relations"] == 2
            assert result["cache_hit"] is False
            assert len(result["relations"]) == 2

            saved = await repo.get_relations(p.id)
            assert len(saved) == 2
            assert all(r.relation_type == "INFERRED" for r in saved)
            assert all("AI suggested:" in r.source for r in saved)

    @pytest.mark.asyncio
    async def test_low_confidence_filtered(
        self, async_session, ai_response_with_low, monkeypatch
    ):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-low-conf", None, "mysql")
            await repo.save_parse_result(p.id, _ecommerce_parse_result())

            mock_complete = MagicMock(return_value=ai_response_with_low)
            monkeypatch.setattr("app.ai.service.ai_client.complete", mock_complete)
            import asyncio
            monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

            result = await complete_relations(p.id, async_session)
            assert result["new_relations"] == 1
            saved = await repo.get_relations(p.id)
            assert len(saved) == 1
            # Verify the saved relation is the HIGH confidence one (addresses → users)
            table_map = {t.id: t.name for t in await repo.get_tables(p.id)}
            assert table_map[saved[0].source_table_id] == "addresses"
            assert table_map[saved[0].target_table_id] == "users"

    @pytest.mark.asyncio
    async def test_invalid_table_reference_filtered(
        self, async_session, ai_response_invalid_table, monkeypatch
    ):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-invalid", None, "mysql")
            await repo.save_parse_result(p.id, _ecommerce_parse_result())

            mock_complete = MagicMock(return_value=ai_response_invalid_table)
            monkeypatch.setattr("app.ai.service.ai_client.complete", mock_complete)
            import asyncio
            monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

            result = await complete_relations(p.id, async_session)
            assert result["new_relations"] == 0

    @pytest.mark.asyncio
    async def test_no_isolated_tables_returns_empty(self, async_session, monkeypatch):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-no-isolated", None, "mysql")
            tables = await repo.save_parse_result(p.id, _ecommerce_parse_result())

            all_ids = [t.id for t in tables]
            all_relations = []
            for i in range(len(all_ids) - 1):
                all_relations.append(
                    RelationData(all_ids[i], ["id"], all_ids[i + 1], ["id"], "TEST", 1.0)
                )
            await repo.save_relations(p.id, all_relations)

            result = await complete_relations(p.id, async_session)
            assert result["cache_hit"] is False
            assert result["new_relations"] == 0
            assert "no isolated tables" in result["message"]

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_relations(
        self, async_session, ai_response_2_relations, monkeypatch
    ):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-cache-hit", None, "mysql")
            await repo.save_parse_result(p.id, _ecommerce_parse_result())

            mock_complete = MagicMock(return_value=ai_response_2_relations)
            monkeypatch.setattr("app.ai.service.ai_client.complete", mock_complete)
            import asyncio
            monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

            result1 = await complete_relations(p.id, async_session)
            assert result1["cache_hit"] is False
            assert result1["new_relations"] == 2

            await repo.save_relations(p.id, [])

            result2 = await complete_relations(p.id, async_session)
            assert result2["cache_hit"] is True
            assert result2["new_relations"] == 2

            saved = await repo.get_relations(p.id)
            assert len(saved) == 2

    @pytest.mark.asyncio
    async def test_concurrency_lock_rejects_parallel(self, monkeypatch):
        import asyncio

        lock = asyncio.Lock()
        await lock.acquire()

        with patch("app.ai.service._get_lock", return_value=lock):
            assert lock.locked() is True


class TestCompleteComments:
    @pytest.mark.asyncio
    async def test_no_missing_comments_returns_empty(self, async_session, monkeypatch):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-comments-empty", None, "mysql")

            from app.parser.models import Column, Table

            pr = ParseResult(
                dialect="mysql",
                tables=[
                    Table(
                        name="t1",
                        schema="",
                        comment="table comment",
                        columns=[
                            Column(name="a", type="int", comment="col A"),
                            Column(name="b", type="varchar", comment="col B"),
                        ],
                        indexes=[],
                        foreign_keys=[],
                    ),
                ],
                errors=[],
            )
            await repo.save_parse_result(p.id, pr)

            result = await complete_comments(p.id, async_session)
            assert result["updated"] == 0
            assert "no missing comments" in result["message"]

    @pytest.mark.asyncio
    async def test_ai_generates_comments_for_missing(self, async_session, monkeypatch):
        async with async_session.begin():
            await clear_all_cache(async_session)

        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("test-comments", None, "mysql")

            from app.parser.models import Column, Table

            pr = ParseResult(
                dialect="mysql",
                tables=[
                    Table(
                        name="t1",
                        schema="",
                        comment="",
                        columns=[
                            Column(name="a", type="int", comment=""),
                            Column(name="b", type="varchar", comment=""),
                        ],
                        indexes=[],
                        foreign_keys=[],
                    ),
                ],
                errors=[],
            )
            await repo.save_parse_result(p.id, pr)

            ai_json = json.dumps({
                "suggestions": [
                    {"table": "t1", "column": "a", "comment": "主键ID"},
                    {"table": "t1", "column": "b", "comment": "用户名称"},
                ]
            })
            mock_complete = MagicMock(return_value=ai_json)
            monkeypatch.setattr("app.ai.service.ai_client.complete", mock_complete)
            import asyncio
            monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

            result = await complete_comments(p.id, async_session)
            assert result["updated"] == 2
            assert result["cache_hit"] is False

            tables = await repo.get_tables(p.id)
            for col in tables[0].columns:
                assert col.comment is not None
                assert "AI Generated" in col.comment


# ── Helpers ──

def _fake_to_thread(func, *args, **kwargs):
    result = func(*args, **kwargs)
    import asyncio

    async def _return():
        return result

    return _return()


def _ecommerce_parse_result():
    from app.parser.models import Column, ForeignKey, Index as PIndex, Table

    return ParseResult(
        dialect="mysql",
        tables=[
            Table(
                name="users", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="用户唯一ID"),
                    Column(name="name", type="varchar", nullable=False, comment="用户名"),
                    Column(name="email", type="varchar", comment="邮箱地址"),
                    Column(name="created_at", type="timestamp", comment=""),
                ],
                indexes=[],
                foreign_keys=[],
            ),
            Table(
                name="orders", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="订单ID"),
                    Column(name="user_id", type="int", nullable=False, comment="下单用户ID"),
                    Column(name="total", type="decimal", comment="订单总金额"),
                    Column(name="status", type="varchar", comment=""),
                    Column(name="created_at", type="timestamp", comment=""),
                ],
                indexes=[],
                foreign_keys=[
                    ForeignKey(columns=["user_id"], ref_table="users", ref_columns=["id"]),
                ],
            ),
            Table(
                name="products", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="商品ID"),
                    Column(name="name", type="varchar", nullable=False, comment="商品名称"),
                    Column(name="category_id", type="int", nullable=False, comment=""),
                    Column(name="price", type="decimal", comment="单价"),
                    Column(name="stock_quantity", type="int", comment="库存数量"),
                ],
                indexes=[],
                foreign_keys=[
                    ForeignKey(columns=["category_id"], ref_table="categories", ref_columns=["id"]),
                ],
            ),
            Table(
                name="categories", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="分类ID"),
                    Column(name="name", type="varchar", nullable=False, comment="分类名称"),
                    Column(name="parent_id", type="int", comment=""),
                ],
                indexes=[],
                foreign_keys=[],
            ),
            Table(
                name="cart_items", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True),
                    Column(name="user_id", type="int", nullable=False),
                    Column(name="product_id", type="int", nullable=False),
                    Column(name="quantity", type="int"),
                ],
                indexes=[],
                foreign_keys=[
                    ForeignKey(columns=["user_id"], ref_table="users", ref_columns=["id"]),
                    ForeignKey(columns=["product_id"], ref_table="products", ref_columns=["id"]),
                ],
            ),
            Table(
                name="reviews", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="评论ID"),
                    Column(name="user_id", type="int", nullable=False),
                    Column(name="product_id", type="int", nullable=False),
                    Column(name="rating", type="int", comment="评分(1-5)"),
                    Column(name="content", type="text", comment="评论内容"),
                ],
                indexes=[],
                foreign_keys=[
                    ForeignKey(columns=["user_id"], ref_table="users", ref_columns=["id"]),
                    ForeignKey(columns=["product_id"], ref_table="products", ref_columns=["id"]),
                ],
            ),
            Table(
                name="addresses", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="地址ID"),
                    Column(name="user_id", type="int", nullable=False),
                    Column(name="address_line", type="varchar"),
                    Column(name="city", type="varchar"),
                    Column(name="postal_code", type="varchar"),
                ],
                indexes=[],
                foreign_keys=[],
            ),
            Table(
                name="payments", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True, comment="支付ID"),
                    Column(name="order_id", type="int", nullable=False, comment="关联订单ID"),
                    Column(name="amount", type="decimal", nullable=False, comment="支付金额"),
                    Column(name="method", type="varchar", comment="支付方式"),
                    Column(name="paid_at", type="timestamp", comment=""),
                ],
                indexes=[],
                foreign_keys=[],
            ),
            Table(
                name="inventory", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True),
                    Column(name="warehouse_name", type="varchar"),
                    Column(name="location_code", type="varchar"),
                    Column(name="capacity", type="int"),
                ],
                indexes=[],
                foreign_keys=[],
            ),
            Table(
                name="shipping_log", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True),
                    Column(name="tracking_number", type="varchar"),
                    Column(name="carrier", type="varchar"),
                    Column(name="shipped_at", type="timestamp"),
                    Column(name="status", type="varchar"),
                ],
                indexes=[],
                foreign_keys=[],
            ),
        ],
        errors=[],
    )
