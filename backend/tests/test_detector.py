import pytest
from app.detector.relation import RelationDetector, _singularize, detect_relations
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
async def test_id_suffix_exact_match(async_session):
    """user_id should match a table named 'user' with confidence=0.85."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("id-exact", None, "mysql")
        sql = """
        CREATE TABLE user (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE post (id INT PRIMARY KEY, user_id INT, title VARCHAR(255));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        inferred = [r for r in relations if r.relation_type == "INFERRED" and r.confidence == 0.85]
        assert len(inferred) >= 1


@pytest.mark.asyncio
async def test_id_suffix_plural_match(async_session):
    """category_id should match 'categories' via singularization with confidence=0.70."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("id-plural", None, "mysql")
        sql = """
        CREATE TABLE categories (id INT PRIMARY KEY, name VARCHAR(255));
        CREATE TABLE posts (id INT PRIMARY KEY, category_id INT, title VARCHAR(255));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        inferred = [r for r in relations if r.confidence == 0.70]
        assert len(inferred) >= 1


@pytest.mark.asyncio
async def test_same_name_same_type_inference(async_session):
    """Two tables with same-named, same-typed non-PK column should get 0.60 relation."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("same-name", None, "mysql")
        sql = """
        CREATE TABLE org_a (id INT PRIMARY KEY, org_id INT);
        CREATE TABLE org_b (id INT PRIMARY KEY, org_id INT);
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        same = [r for r in relations if r.confidence == 0.60]
        assert len(same) >= 1


@pytest.mark.asyncio
async def test_nm_bridge_table_marking(async_session):
    """A table with exactly 2 FKs and <=5 columns should be marked N:M."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("nm-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY);
        CREATE TABLE roles (id INT PRIMARY KEY);
        CREATE TABLE user_roles (id INT PRIMARY KEY, user_id INT, role_id INT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        nm_rels = [r for r in relations if r.source and "N:M" in r.source]
        assert len(nm_rels) >= 1


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
async def test_dedup_keeps_highest_confidence(async_session):
    """Duplicate relations should keep only the highest confidence entry."""
    repo = Repository(async_session)
    async with async_session.begin():
        p = await repo.create_project("dedup-test", None, "mysql")
        sql = """
        CREATE TABLE users (id INT PRIMARY KEY);
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT,
            FOREIGN KEY (user_id) REFERENCES users(id));
        """
        parser = MySQLParser()
        result = parser.parse(sql)
        await repo.save_parse_result(p.id, result)

        relations = await detect_relations(p.id, async_session)
        # There should be exactly one orders.user_id → users.id relation
        pairs = [r for r in relations if r.source_columns == ["user_id"] and r.target_columns == ["id"]]
        assert len(pairs) == 1
        assert pairs[0].confidence == 1.0  # FK wins over inferred


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


class TestSingularize:
    def test_basic_plural(self):
        assert _singularize("users") == "user"
        assert _singularize("posts") == "post"

    def test_ies_ending(self):
        assert _singularize("categories") == "category"
        assert _singularize("companies") == "company"

    def test_es_ending(self):
        assert _singularize("boxes") == "box"
        assert _singularize("statuses") == "status"
        assert _singularize("classes") == "class"

    def test_no_change(self):
        assert _singularize("user") == "user"
        assert _singularize("data") == "data"
        assert _singularize("ss") == "ss"
