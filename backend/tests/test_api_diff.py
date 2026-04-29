"""Tests for the version diff API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.db.engine import init_db
from app.main import app


@pytest_asyncio.fixture
async def api_db():
    await init_db()
    yield


@pytest.mark.asyncio
async def _create_version(client, project_id, sql, tag=None):
    body = {"sql_content": sql}
    if tag:
        body["version_tag"] = tag
    return await client.post(f"/api/projects/{project_id}/versions", json=body)


SIMPLE_SQL = """
    CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));
    CREATE TABLE orders (id INT PRIMARY KEY, total DECIMAL(10,2));
"""

V2_SQL = """
    CREATE TABLE users (id BIGINT PRIMARY KEY, name VARCHAR(255));
    CREATE TABLE orders (id INT PRIMARY KEY, total DECIMAL(10,2), coupon_id INT);
    CREATE TABLE coupons (id INT PRIMARY KEY, code VARCHAR(50));
"""


# ── Version CRUD ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestVersionCreate:
    async def test_create_version(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-test"})
            pid = proj.json()["id"]

            resp = await client.post(f"/api/projects/{pid}/versions", json={"sql_content": SIMPLE_SQL})
            assert resp.status_code == 201
            data = resp.json()
            assert data["project_id"] == pid
            assert data["tables_count"] == 2
            assert data["version_tag"] is not None

    async def test_create_version_with_tag(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-tag"})
            pid = proj.json()["id"]

            resp = await client.post(f"/api/projects/{pid}/versions", json={
                "sql_content": SIMPLE_SQL, "version_tag": "v1.0",
            })
            assert resp.status_code == 201
            assert resp.json()["version_tag"] == "v1.0"

    async def test_create_version_404(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/projects/nonexistent/versions", json={"sql_content": SIMPLE_SQL})
            assert resp.status_code == 404


@pytest.mark.asyncio
class TestVersionList:
    async def test_list_versions(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-list"})
            pid = proj.json()["id"]

            await _create_version(client, pid, SIMPLE_SQL)
            await _create_version(client, pid, V2_SQL)

            resp = await client.get(f"/api/projects/{pid}/versions")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2

    async def test_list_versions_empty(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-empty"})
            pid = proj.json()["id"]

            resp = await client.get(f"/api/projects/{pid}/versions")
            assert resp.status_code == 200
            assert resp.json()["total"] == 0


@pytest.mark.asyncio
class TestVersionDelete:
    async def test_delete_version(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-del"})
            pid = proj.json()["id"]
            created = await _create_version(client, pid, SIMPLE_SQL)
            vid = created.json()["id"]

            resp = await client.delete(f"/api/projects/{pid}/versions/{vid}")
            assert resp.status_code == 204

            list_resp = await client.get(f"/api/projects/{pid}/versions")
            assert list_resp.json()["total"] == 0

    async def test_delete_version_404(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-del-404"})
            pid = proj.json()["id"]
            resp = await client.delete(f"/api/projects/{pid}/versions/nonexistent")
            assert resp.status_code == 404


# ── Diff CRUD ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDiffCreate:
    async def test_create_diff(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-create"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()
            v2 = (await _create_version(client, pid, V2_SQL)).json()

            resp = await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v2["id"],
            })
            assert resp.status_code == 201
            data = resp.json()
            assert data["diff_data"]["summary_stats"]["tables"]["added"] == 1

    async def test_create_diff_identical(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-same"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()

            resp = await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v1["id"],
            })
            assert resp.status_code == 201
            s = resp.json()["diff_data"]["summary_stats"]
            assert s["tables"]["added"] == 0
            assert s["fields"]["modified"] == 0

    async def test_create_diff_version_404(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-404"})
            pid = proj.json()["id"]
            resp = await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": "bad", "new_version_id": "bad",
            })
            assert resp.status_code == 404


@pytest.mark.asyncio
class TestDiffGet:
    async def test_get_diff(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-get"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()
            v2 = (await _create_version(client, pid, V2_SQL)).json()
            diff = (await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v2["id"],
            })).json()

            resp = await client.get(f"/api/projects/{pid}/diff/{diff['id']}")
            assert resp.status_code == 200
            assert resp.json()["id"] == diff["id"]

    async def test_get_diff_404(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-get-404"})
            pid = proj.json()["id"]
            resp = await client.get(f"/api/projects/{pid}/diff/nonexistent")
            assert resp.status_code == 404


@pytest.mark.asyncio
class TestDiffList:
    async def test_list_diffs(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-list"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()
            v2 = (await _create_version(client, pid, V2_SQL)).json()
            await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v2["id"],
            })

            resp = await client.get(f"/api/projects/{pid}/diffs")
            assert resp.status_code == 200
            assert resp.json()["total"] >= 1


# ── Migration export ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestMigrationEndpoint:
    async def test_export_migration(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-mig"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()
            v2 = (await _create_version(client, pid, V2_SQL)).json()
            diff = (await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v2["id"],
            })).json()

            resp = await client.post(f"/api/projects/{pid}/diff/{diff['id']}/migration")
            assert resp.status_code == 200
            assert "CREATE TABLE" in resp.text

    async def test_export_migration_404(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-mig-404"})
            pid = proj.json()["id"]
            resp = await client.post(f"/api/projects/{pid}/diff/nonexistent/migration")
            assert resp.status_code == 404


# ── AI Summary endpoint ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestAISummary:
    async def test_ai_summary_disabled(self, api_db):
        from app.config import settings
        original = settings.ai_enabled
        settings.ai_enabled = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-ai"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()
            v2 = (await _create_version(client, pid, V2_SQL)).json()
            diff = (await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v2["id"],
            })).json()

            resp = await client.post(f"/api/projects/{pid}/diff/{diff['id']}/ai-summary")
            assert resp.status_code == 503

        settings.ai_enabled = original

    async def test_ai_summary_404(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-ai-404"})
            pid = proj.json()["id"]
            resp = await client.post(f"/api/projects/{pid}/diff/nonexistent/ai-summary")
            assert resp.status_code == 404


# ── Cascade delete ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCascadeDelete:
    async def test_delete_project_cascades(self, api_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj = await client.post("/api/projects", json={"name": "diff-cascade"})
            pid = proj.json()["id"]
            v1 = (await _create_version(client, pid, SIMPLE_SQL)).json()
            v2 = (await _create_version(client, pid, V2_SQL)).json()
            diff = (await client.post(f"/api/projects/{pid}/diff", json={
                "old_version_id": v1["id"], "new_version_id": v2["id"],
            })).json()

            await client.delete(f"/api/projects/{pid}")

            resp_v = await client.get(f"/api/projects/{pid}/versions")
            assert resp_v.status_code == 404
            resp_d = await client.get(f"/api/projects/{pid}/diffs")
            assert resp_d.status_code == 404
