import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.store.repository import Repository


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_preview_relations(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("query-rel-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, total DECIMAL);
        """
        from app.parser import MySQLParser
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

    response = await async_client.post(
        f"/api/projects/{p.id}/query-relations",
        json={
            "sql": "SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["queries_parsed"] == 1
    assert len(data["relations"]) == 1
    r = data["relations"][0]
    assert r["source_table"] == "users"
    assert r["target_table"] == "orders"
    assert r["source_columns"] == ["id"]
    assert r["target_columns"] == ["user_id"]
    assert r["join_type"] == "LEFT JOIN"
    assert r["confidence"] == 1.0
    assert r["already_exists"] is False


@pytest.mark.asyncio
async def test_preview_unmatched_tables(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("unmatched-test", None, "mysql")
        sql = "CREATE TABLE users (id INT PRIMARY KEY);"
        from app.parser import MySQLParser
        parser = MySQLParser()
        await repo.save_parse_result(p.id, parser.parse(sql))

    response = await async_client.post(
        f"/api/projects/{p.id}/query-relations",
        json={"sql": "SELECT * FROM users u JOIN logs l ON u.id = l.user_id"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["unmatched_tables"]) >= 1


@pytest.mark.asyncio
async def test_preview_project_not_found(async_client: AsyncClient):
    response = await async_client.post(
        "/api/projects/nonexistent/query-relations",
        json={"sql": "SELECT * FROM users"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_invalid_sql(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("invalid-sql-test", None, "mysql")
        sql = "CREATE TABLE users (id INT PRIMARY KEY);"
        from app.parser import MySQLParser
        await repo.save_parse_result(p.id, MySQLParser().parse(sql))

    response = await async_client.post(
        f"/api/projects/{p.id}/query-relations",
        json={"sql": "CRATE TABLE t (id INT)"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_save_relations(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("save-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, total DECIMAL);
        """
        from app.parser import MySQLParser
        await repo.save_parse_result(p.id, MySQLParser().parse(sql))

    sql_query = "SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id"

    # Step 1: Preview
    preview_resp = await async_client.post(
        f"/api/projects/{p.id}/query-relations",
        json={"sql": sql_query},
    )
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    temp_id = preview_data["relations"][0]["temp_id"]

    # Step 2: Save
    save_resp = await async_client.post(
        f"/api/projects/{p.id}/query-relations/save",
        json={"sql": sql_query, "relation_ids": [temp_id]},
    )
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["saved"] == 1
    assert save_data["skipped"] == 0

    # Step 3: Verify via GET /relations
    from app.db.engine import get_db
    async for db in get_db():
        repo2 = Repository(db)
        relations = await repo2.get_relations(p.id)
        assert len(relations) == 1
        assert relations[0].relation_type == "QUERY_INFERRED"
        break


@pytest.mark.asyncio
async def test_save_duplicate_skipped(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("dedup-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, total DECIMAL);
        """
        from app.parser import MySQLParser
        await repo.save_parse_result(p.id, MySQLParser().parse(sql))

    sql_query = "SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id"

    # Save once
    preview1 = await async_client.post(f"/api/projects/{p.id}/query-relations", json={"sql": sql_query})
    tid1 = preview1.json()["relations"][0]["temp_id"]
    await async_client.post(
        f"/api/projects/{p.id}/query-relations/save",
        json={"sql": sql_query, "relation_ids": [tid1]},
    )

    # Save again (same relation)
    preview2 = await async_client.post(f"/api/projects/{p.id}/query-relations", json={"sql": sql_query})
    tid2 = preview2.json()["relations"][0]["temp_id"]
    save2 = await async_client.post(
        f"/api/projects/{p.id}/query-relations/save",
        json={"sql": sql_query, "relation_ids": [tid2]},
    )
    data = save2.json()
    assert data["saved"] == 0
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_save_invalid_temp_id(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("bad-id-test", None, "mysql")
        sql = "CREATE TABLE users (id INT PRIMARY KEY);"
        from app.parser import MySQLParser
        await repo.save_parse_result(p.id, MySQLParser().parse(sql))

    response = await async_client.post(
        f"/api/projects/{p.id}/query-relations/save",
        json={"sql": "SELECT * FROM users", "relation_ids": ["nonexistent"]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_save_project_not_found(async_client: AsyncClient):
    response = await async_client.post(
        "/api/projects/nonexistent/query-relations/save",
        json={"sql": "SELECT * FROM users", "relation_ids": ["r1"]},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_already_exists_flag(async_client: AsyncClient, async_session):
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("exists-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, total DECIMAL);
        """
        from app.parser import MySQLParser
        await repo.save_parse_result(p.id, MySQLParser().parse(sql))

    sql_query = "SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id"

    # Preview → Save
    preview1 = await async_client.post(f"/api/projects/{p.id}/query-relations", json={"sql": sql_query})
    tid1 = preview1.json()["relations"][0]["temp_id"]
    await async_client.post(
        f"/api/projects/{p.id}/query-relations/save",
        json={"sql": sql_query, "relation_ids": [tid1]},
    )

    # Preview again — should show already_exists=True
    preview2 = await async_client.post(f"/api/projects/{p.id}/query-relations", json={"sql": sql_query})
    assert preview2.json()["relations"][0]["already_exists"] is True
