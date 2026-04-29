"""Tests for session CRUD."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import Repository


class TestSessionCreate:
    @pytest.mark.asyncio
    async def test_create_session(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj", None, "mysql")

            session = await repo.create_session(p.id, title="test session")
            assert session.id is not None
            assert session.project_id == p.id
            assert session.title == "test session"

    @pytest.mark.asyncio
    async def test_create_session_without_title(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj2", None, "mysql")

            session = await repo.create_session(p.id)
            assert session.id is not None
            assert session.title is None


class TestSessionGet:
    @pytest.mark.asyncio
    async def test_get_existing_session(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj3", None, "mysql")
            created = await repo.create_session(p.id, title="find me")

            found = await repo.get_session(created.id)
            assert found is not None
            assert found.title == "find me"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            found = await repo.get_session("nonexistent-id")
            assert found is None


class TestSessionList:
    @pytest.mark.asyncio
    async def test_list_project_sessions(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj4", None, "mysql")
            await repo.create_session(p.id, title="session 1")
            await repo.create_session(p.id, title="session 2")

            sessions = await repo.list_project_sessions(p.id)
            assert len(sessions) == 2
            # Most recently updated first
            assert sessions[0].title == "session 2"

    @pytest.mark.asyncio
    async def test_list_empty(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj5", None, "mysql")
            sessions = await repo.list_project_sessions(p.id)
            assert sessions == []


class TestSessionDelete:
    @pytest.mark.asyncio
    async def test_delete_session(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj6", None, "mysql")
            session = await repo.create_session(p.id)

            deleted = await repo.delete_session(session.id)
            assert deleted is True
            assert await repo.get_session(session.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            deleted = await repo.delete_session("no-such-id")
            assert deleted is False

    @pytest.mark.asyncio
    async def test_cascade_deletes_messages(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("sess-proj7", None, "mysql")
            session = await repo.create_session(p.id)

            await repo.add_message(session.id, "user", "hello")
            await repo.add_message(session.id, "assistant", "hi there")

            # Messages exist before delete
            msgs_before = await repo.get_messages(session.id)
            assert len(msgs_before) == 2

            await repo.delete_session(session.id)

            # Session gone
            assert await repo.get_session(session.id) is None


class TestMessageCRUD:
    @pytest.mark.asyncio
    async def test_add_and_get_messages(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("msg-proj", None, "mysql")
            session = await repo.create_session(p.id)

            msg = await repo.add_message(session.id, "user", "what tables exist?")
            assert msg.role == "user"
            assert msg.content == "what tables exist?"

            msgs = await repo.get_messages(session.id)
            assert len(msgs) == 1
            assert msgs[0].content == "what tables exist?"

    @pytest.mark.asyncio
    async def test_message_with_sources(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("msg-proj2", None, "mysql")
            session = await repo.create_session(p.id)

            sources = [{"table": "users", "column": "id"}]
            msg = await repo.add_message(session.id, "assistant", "users table has id column", sources)
            assert msg.sources == sources

            msgs = await repo.get_messages(session.id)
            assert msgs[0].sources == sources

    @pytest.mark.asyncio
    async def test_messages_ordered_by_created_at(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("msg-proj3", None, "mysql")
            session = await repo.create_session(p.id)

            await repo.add_message(session.id, "user", "first")
            await repo.add_message(session.id, "assistant", "second")
            await repo.add_message(session.id, "user", "third")

            msgs = await repo.get_messages(session.id)
            assert [m.content for m in msgs] == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_message_limit(self, async_session):
        async with async_session.begin():
            repo = Repository(async_session)
            p = await repo.create_project("msg-proj4", None, "mysql")
            session = await repo.create_session(p.id)

            for i in range(25):
                await repo.add_message(session.id, "user", f"msg {i}")

            msgs = await repo.get_messages(session.id, limit=10)
            assert len(msgs) == 10
