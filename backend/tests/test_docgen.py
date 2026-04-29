"""Tests for document generation (markdown data dictionary)."""

import json
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.store.repository import Repository


@pytest_asyncio.fixture
async def project_with_full_schema(async_session):
    """Create a project with sample schema for doc generation testing."""
    from app.parser.models import Column, ForeignKey, Index, Table

    async with async_session.begin():
        repo = Repository(async_session)
        p = await repo.create_project("doc-proj", None, "mysql")
        pr = ParseResult(
            dialect="mysql",
            tables=[
                Table(
                    name="users", schema="public", comment="用户信息表",
                    columns=[
                        Column(name="id", type="int", primary_key=True, comment="用户唯一标识"),
                        Column(name="name", type="varchar", nullable=False, comment="用户名"),
                        Column(name="email", type="varchar", comment="电子邮箱"),
                    ],
                    indexes=[
                        Index(name="idx_email", unique=True, columns=["email"]),
                    ],
                    foreign_keys=[],
                ),
                Table(
                    name="orders", schema="public", comment="",
                    columns=[
                        Column(name="id", type="int", primary_key=True, comment="订单ID"),
                        Column(name="user_id", type="int", nullable=False, comment="关联用户"),
                        Column(name="total", type="decimal", comment="订单金额"),
                        Column(name="status", type="varchar", comment=""),
                    ],
                    indexes=[],
                    foreign_keys=[
                        ForeignKey(columns=["user_id"], ref_table="users", ref_columns=["id"]),
                    ],
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
                source="explicit FK",
            ),
        ])

    return p.id


class TestDocGenerationTemplate:
    @pytest.mark.asyncio
    async def test_pure_template_contains_all_sections(self, project_with_full_schema):
        """Template mode (no AI) generates complete data dictionary."""
        project_id = project_with_full_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": False, "title": "Test Doc"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["title"] == "Test Doc"
            assert data["ai_enhanced"] is False
            assert data["doc_type"] == "markdown"
            assert len(data["content_snippet"]) > 0

            doc_id = data["id"]

        # Fetch the full doc content
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/projects/{project_id}/docs/{doc_id}")
            assert resp.status_code == 200
            content = resp.text

            # Verify structure
            assert "# 数据字典 - doc-proj" in content
            assert "## 一、项目概览" in content
            assert "## 二、表结构详情" in content
            assert "## 三、关联关系" in content

            # Verify tables present
            assert "users" in content
            assert "orders" in content

            # Verify columns present
            assert "id" in content
            assert "name" in content
            assert "email" in content
            assert "user_id" in content
            assert "total" in content

            # Verify indexes
            assert "idx_email" in content
            assert "UNIQUE" in content

            # Verify relations
            assert "FOREIGN_KEY" in content

            # No AI markers
            assert "AI Generated" not in content

    @pytest.mark.asyncio
    async def test_default_title_generated(self, project_with_full_schema):
        project_id = project_with_full_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": False},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert "doc-proj" in data["title"]
            assert "数据字典" in data["title"]

    @pytest.mark.asyncio
    async def test_nonexistent_project_returns_404(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/projects/nonexistent/docs",
                json={"ai_enhance": False},
            )
            assert resp.status_code == 404


class TestDocCRUD:
    @pytest.mark.asyncio
    async def test_list_docs(self, project_with_full_schema):
        project_id = project_with_full_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create 2 docs
            await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": False, "title": "Doc A"},
            )
            await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": False, "title": "Doc B"},
            )

            resp = await client.get(f"/api/projects/{project_id}/docs")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
            # Most recent first
            assert data["items"][0]["title"] == "Doc B"

    @pytest.mark.asyncio
    async def test_delete_doc(self, project_with_full_schema):
        project_id = project_with_full_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": False, "title": "To Delete"},
            )
            doc_id = resp.json()["id"]

            # Delete
            resp2 = await client.delete(f"/api/projects/{project_id}/docs/{doc_id}")
            assert resp2.status_code == 204

            # Verify gone
            resp3 = await client.get(f"/api/projects/{project_id}/docs/{doc_id}")
            assert resp3.status_code == 404

            # List is empty
            resp4 = await client.get(f"/api/projects/{project_id}/docs")
            assert resp4.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_get_doc_wrong_project_returns_404(self, async_session, project_with_full_schema):
        project_id = project_with_full_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create doc in project A
            resp = await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": False},
            )
            doc_id = resp.json()["id"]

        # Try to access from project B
        async with async_session.begin():
            repo = Repository(async_session)
            p2 = await repo.create_project("other-proj", None, "mysql")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/api/projects/{p2.id}/docs/{doc_id}")
            assert resp.status_code == 404


class TestDocAIEnhanced:
    @pytest.mark.asyncio
    async def test_ai_enhance_fault_tolerant(self, project_with_full_schema, monkeypatch):
        """When AI calls fail, document should still be generated."""
        # Make all AI service functions raise errors
        async def _raise(*args, **kwargs):
            raise RuntimeError("AI unavailable")

        monkeypatch.setattr("app.ai.service.generate_project_summary", _raise)
        monkeypatch.setattr("app.ai.service.generate_table_descriptions", _raise)
        monkeypatch.setattr("app.ai.service.complete_comments", _raise)

        project_id = project_with_full_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/docs",
                json={"ai_enhance": True, "title": "AI Doc"},
            )
            # Should still succeed (fault-tolerant)
            assert resp.status_code == 201
            data = resp.json()
            assert data["ai_enhanced"] is True
            assert data["title"] == "AI Doc"


# ── Helpers ──

from app.parser.models import ParseResult
