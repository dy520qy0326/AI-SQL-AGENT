import pytest
from app.detector.relation import RelationDetector, detect_relations
from app.store.repository import Repository
from app.parser.models import ParseResult
from app.parser import MySQLParser


@pytest.mark.asyncio
async def test_explicit_fk_detection(async_session):
    """All explicit FKs should be detected with confidence=1.0."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("fk-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        fk_rels = [r for r in relations if r.relation_type == "FOREIGN_KEY"]
        assert len(fk_rels) == 1
        assert fk_rels[0].confidence == 1.0
        assert fk_rels[0].source_columns == ["user_id"]
        assert fk_rels[0].target_columns == ["id"]


@pytest.mark.asyncio
async def test_self_referencing_fk(async_session):
    """Self-referencing FK should be detected."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("self-ref", None, "mysql")
        sql = """
        CREATE TABLE categories (id INT PRIMARY KEY, parent_id INT,
            FOREIGN KEY (parent_id) REFERENCES categories(id));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        fk_rels = [r for r in relations if r.relation_type == "FOREIGN_KEY"]
        assert len(fk_rels) == 1
        assert fk_rels[0].source_table_id == fk_rels[0].target_table_id


@pytest.mark.asyncio
async def test_no_relation_for_missing_target(async_session):
    """An FK referencing a table not in the project should be ignored."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("missing-target", None, "mysql")
        sql = """
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT,
            FOREIGN KEY (user_id) REFERENCES nonexistent_table(id));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        assert len(relations) == 0


@pytest.mark.asyncio
async def test_multi_fk_detection(async_session):
    """Multiple FKs between different tables should all be detected."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("multi-fk", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY);
        CREATE TABLE products (id INT PRIMARY KEY);
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, product_id INT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        assert len(relations) == 2
        types = {r.source_columns[0] for r in relations}
        assert types == {"user_id", "product_id"}
