"""Tests for NL Query /ask endpoints (SSE + sync)."""

import json
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIClient
from app.main import app
from app.store.repository import Repository


@pytest_asyncio.fixture
async def project_with_schema(async_session):
    """Create a project with sample tables."""
    from app.parser.models import Column, ForeignKey, Table

    async with async_session.begin():
        repo = Repository(async_session)
        p = await repo.create_project("ask-proj", None, "mysql")
        pr = _simple_parse_result()
        await repo.save_parse_result(p.id, pr)

    return p.id


@pytest.fixture
def mock_ai_stream():
    """Mock ai_client.complete_stream to yield chunks."""
    import app.nl.router

    original = getattr(app.nl.router.ai_client, "complete_stream", None)

    def _fake_stream(system_prompt, user_message, max_tokens=None, model=None):
        yield "orders 表包含以下字段："
        yield "id, user_id, total, status"
        yield "\n```sources\n"
        yield '[{"table": "orders", "column": "id"}]\n'
        yield "```"

    app.nl.router.ai_client.complete_stream = _fake_stream
    yield
    if original:
        app.nl.router.ai_client.complete_stream = original


@pytest.fixture
def mock_ai_complete():
    """Mock ai_client.complete to return a full response."""
    import app.nl.router

    original = getattr(app.nl.router.ai_client, "complete", None)

    def _fake_complete(system_prompt, user_message, max_tokens=None, temperature=None, model=None):
        return '该数据库包含 users 和 orders 两张表。\n```sources\n[{"table": "users"}, {"table": "orders"}]\n```'

    app.nl.router.ai_client.complete = _fake_complete
    yield
    if original:
        app.nl.router.ai_client.complete = original


@pytest.fixture
def ai_enabled(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")


@pytest.fixture
def ai_disabled(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ai_enabled", False)


class TestAskSync:
    @pytest.mark.asyncio
    async def test_sync_returns_answer(self, ai_enabled, project_with_schema, mock_ai_complete):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask/sync",
                json={"question": "这个数据库有哪些表"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "answer" in data
            assert "users" in data["answer"]
            assert len(data["sources"]) == 2
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_sync_empty_question_returns_400(self, ai_enabled, project_with_schema):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask/sync",
                json={"question": "   "},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_ai_disabled_returns_503(self, ai_disabled, project_with_schema):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask/sync",
                json={"question": "有哪些表"},
            )
            assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_sync_nonexistent_session_returns_404(self, ai_enabled, project_with_schema):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask/sync",
                json={"question": "hi", "session_id": "nonexistent"},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_creates_session_automatically(self, ai_enabled, project_with_schema, mock_ai_complete):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask/sync",
                json={"question": "有什么表"},
            )
            assert resp.status_code == 200
            session_id = resp.json()["session_id"]
            assert session_id is not None

            # Verify session was created
            resp2 = await client.get(f"/api/sessions/{session_id}/messages")
            assert resp2.status_code == 200
            msgs = resp2.json()["items"]
            assert len(msgs) == 2  # user + assistant


class TestAskSSE:
    @pytest.mark.asyncio
    async def test_sse_returns_stream(self, ai_enabled, project_with_schema, mock_ai_stream):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask",
                json={"question": "orders 表有哪些字段"},
            )
            assert resp.status_code == 200

            # Parse SSE events
            text = resp.text
            lines = [l for l in text.split("\n") if l.startswith("data: ")]
            assert len(lines) > 0

            # First chunk should have content
            first = json.loads(lines[0][6:])
            assert first["type"] == "chunk"

            # Last event should be "done"
            last = json.loads(lines[-1][6:])
            assert last["type"] == "done"

    @pytest.mark.asyncio
    async def test_sse_empty_question_returns_400(self, ai_enabled, project_with_schema):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask",
                json={"question": ""},
            )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sse_ai_disabled_returns_503(self, ai_disabled, project_with_schema):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/projects/{project_id}/ask",
                json={"question": "help"},
            )
            assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_sse_reuses_session(self, ai_enabled, project_with_schema, mock_ai_stream):
        project_id = project_with_schema
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # First request creates a session
            resp1 = await client.post(
                f"/api/projects/{project_id}/ask",
                json={"question": "有哪些表"},
            )
            session_id = resp1.headers.get("x-session-id")
            assert session_id is not None

            # Second request reuses the session
            resp2 = await client.post(
                f"/api/projects/{project_id}/ask",
                json={"question": "继续", "session_id": session_id},
            )
            assert resp2.status_code == 200

            # Verify both messages stored
            resp3 = await client.get(f"/api/sessions/{session_id}/messages")
            msgs = resp3.json()["items"]
            assert len(msgs) == 4  # 2 user + 2 assistant


# ── Helpers ──

def _simple_parse_result():
    from app.parser.models import Column, ForeignKey, Table

    return ParseResult(
        dialect="mysql",
        tables=[
            Table(
                name="users", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True),
                    Column(name="name", type="varchar", nullable=False),
                ],
                indexes=[],
                foreign_keys=[],
            ),
            Table(
                name="orders", schema="", comment="",
                columns=[
                    Column(name="id", type="int", primary_key=True),
                    Column(name="user_id", type="int"),
                ],
                indexes=[],
                foreign_keys=[
                    ForeignKey(columns=["user_id"], ref_table="users", ref_columns=["id"]),
                ],
            ),
        ],
        errors=[],
    )


from app.parser.models import ParseResult
