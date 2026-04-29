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
async def test_graph_endpoint(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "graph-test", "dialect": "mysql"})
        pid = r.json()["id"]

        sql = """CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id));"""
        await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql})

        r = await client.get(f"/api/projects/{pid}/graph")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) >= 1

        for node in data["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "columns" in node
            assert node["column_count"] == len(node["columns"])

        fk_edges = [e for e in data["edges"] if e["type"] == "FOREIGN_KEY"]
        for e in fk_edges:
            assert e["dashes"] is False


@pytest.mark.asyncio
async def test_graph_filtered(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "graph-filter", "dialect": "mysql"})
        pid = r.json()["id"]

        sql = """CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id));
        CREATE TABLE products (id INT PRIMARY KEY, name VARCHAR(255));"""
        await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql})

        r = await client.get(f"/api/projects/{pid}/graph?type=FOREIGN_KEY")
        for e in r.json()["edges"]:
            assert e["type"] == "FOREIGN_KEY"

        r = await client.get(f"/api/projects/{pid}/graph?min_confidence=0.9")
        for e in r.json()["edges"]:
            assert e["confidence"] >= 0.9


@pytest.mark.asyncio
async def test_mermaid_endpoint(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/projects", json={"name": "mermaid-test", "dialect": "mysql"})
        pid = r.json()["id"]

        sql = """CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id));"""
        await client.post(f"/api/projects/{pid}/upload", json={"sql_content": sql})

        r = await client.get(f"/api/projects/{pid}/mermaid")
        assert r.status_code == 200
        text = r.text
        assert text.startswith("erDiagram")
        assert "users" in text
        assert "orders" in text
        assert "PK" in text
        assert "||--o{" in text or "}o--o{" in text


@pytest.mark.asyncio
async def test_graph_404(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/projects/nonexistent/graph")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_mermaid_404(api_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/projects/nonexistent/mermaid")
        assert r.status_code == 404
