import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.db.engine import init_db
from app.main import app


@pytest_asyncio.fixture
async def api_db():
    """Set up DB tables for API tests."""
    await init_db()
    yield


@pytest.mark.asyncio
async def test_create_project(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "api-proj", "dialect": "mysql"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "api-proj"
        assert data["table_count"] == 0


@pytest.mark.asyncio
async def test_list_projects(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/projects")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_get_project_not_found(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/projects/nonexistent-id")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_project(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "to-delete", "dialect": "mysql"})
        pid = r.json()["id"]

        r = await client.delete(f"/api/projects/{pid}")
        assert r.status_code == 204

        r = await client.get(f"/api/projects/{pid}")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_and_get_tables(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "upload-test", "dialect": "mysql"})
        pid = r.json()["id"]

        sql = """CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id));"""
        r = await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql})
        assert r.status_code == 200
        data = r.json()
        assert data["tables_count"] == 2
        assert data["relations_count"] >= 1

        r = await client.get(f"/api/projects/{pid}/tables")
        assert r.status_code == 200
        tables = r.json()
        assert len(tables) == 2
        names = {t["name"] for t in tables}
        assert names == {"users", "orders"}

        tid = tables[0]["id"]
        r = await client.get(f"/api/projects/{pid}/tables/{tid}")
        assert r.status_code == 200
        detail = r.json()
        assert "columns" in detail


@pytest.mark.asyncio
async def test_upload_empty_sql(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "empty-test", "dialect": "mysql"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/upload", json={"sql_content": ""})
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_upload_syntax_error(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "syntax-err", "dialect": "mysql"})
        pid = r.json()["id"]
        r = await client.post(f"/api/projects/{pid}/upload",
                              json={"sql_content": "CREATE TABLE ();"})
        assert r.status_code in (200, 422)


@pytest.mark.asyncio
async def test_upload_nonexistent_project(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects/nonexistent/upload",
                              json={"sql_content": "CREATE TABLE t (id INT);"})
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_relations_filtered(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "rel-filter", "dialect": "mysql"})
        pid = r.json()["id"]

        sql = """CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id));"""
        await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql})

        r = await client.get(f"/api/projects/{pid}/relations")
        assert r.json()["total"] >= 1

        r = await client.get(f"/api/projects/{pid}/relations?type=FOREIGN_KEY")
        for item in r.json()["items"]:
            assert item["relation_type"] == "FOREIGN_KEY"

        r = await client.get(f"/api/projects/{pid}/relations?min_confidence=0.9")
        for item in r.json()["items"]:
            assert item["confidence"] >= 0.9


@pytest.mark.asyncio
async def test_reupload_overwrites(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "reupload", "dialect": "mysql"})
        pid = r.json()["id"]

        sql1 = "CREATE TABLE t1 (id INT PRIMARY KEY);"
        await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql1})

        sql2 = """CREATE TABLE a (id INT PRIMARY KEY);
        CREATE TABLE b (id INT PRIMARY KEY);"""
        r = await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql2})
        assert r.json()["tables_count"] == 2

        r = await client.get(f"/api/projects/{pid}/tables")
        tables = r.json()
        assert len(tables) == 2
        names = {t["name"] for t in tables}
        assert names == {"a", "b"}
