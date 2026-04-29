from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AICache,
    Column as ColumnModel,
    ConversationMessage,
    ConversationSession,
    ForeignKeyModel,
    GeneratedDoc,
    Index as IndexModel,
    Project,
    ProjectVersion,
    Relation,
    SchemaDiff,
    Table,
)
from app.parser.models import ParseResult


@dataclass
class RelationData:
    source_table_id: str
    source_columns: list[str]
    target_table_id: str
    target_columns: list[str]
    relation_type: str
    confidence: float
    source: str | None = None


class Repository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Project ──────────────────────────────────────────────

    async def create_project(self, name: str, description: str | None, dialect: str) -> Project:
        project = Project(name=name, description=description, dialect=dialect)
        self.db.add(project)
        await self.db.flush()
        return project

    async def get_project(self, project_id: str) -> dict | None:
        result = await self.db.execute(
            select(
                Project,
                func.count(func.distinct(Table.id)).label("table_count"),
                func.count(func.distinct(Relation.id)).label("relation_count"),
            )
            .outerjoin(Table, Table.project_id == Project.id)
            .outerjoin(Relation, Relation.project_id == Project.id)
            .where(Project.id == project_id)
            .group_by(Project.id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return {
            **row.Project.__dict__,
            "table_count": row.table_count,
            "relation_count": row.relation_count,
        }

    async def list_projects(self, page: int = 1, size: int = 20) -> tuple[list[dict], int]:
        count_q = select(func.count(Project.id))
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(
                Project,
                func.count(func.distinct(Table.id)).label("table_count"),
                func.count(func.distinct(Relation.id)).label("relation_count"),
            )
            .outerjoin(Table, Table.project_id == Project.id)
            .outerjoin(Relation, Relation.project_id == Project.id)
            .group_by(Project.id)
            .order_by(Project.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await self.db.execute(q)).all()
        projects = []
        for row in rows:
            projects.append({
                **row.Project.__dict__,
                "table_count": row.table_count,
                "relation_count": row.relation_count,
            })
        return projects, total

    async def delete_project(self, project_id: str) -> bool:
        result = await self.db.execute(delete(Project).where(Project.id == project_id))
        await self.db.flush()
        return result.rowcount > 0

    # ── Parse Result persistence ─────────────────────────────

    async def save_parse_result(self, project_id: str, parse_result: ParseResult) -> list[Table]:
        """Batch-write parsed tables/columns/indexes/fks into the project. Returns created Table ORM objects."""
        # Remove existing tables for this project (cascade handles children)
        await self.db.execute(delete(Table).where(Table.project_id == project_id))

        tables = []
        for pt in parse_result.tables:
            table = Table(
                project_id=project_id,
                schema_name=pt.schema_,
                name=pt.name,
                comment=pt.comment or None,
            )
            self.db.add(table)
            await self.db.flush()

            for i, pc in enumerate(pt.columns):
                col = ColumnModel(
                    table_id=table.id,
                    name=pc.name,
                    ordinal_position=i,
                    data_type=pc.type,
                    length=pc.length,
                    nullable=pc.nullable,
                    default_value=pc.default,
                    is_primary_key=pc.primary_key,
                    comment=pc.comment or None,
                )
                self.db.add(col)

            for pidx in pt.indexes:
                idx = IndexModel(
                    table_id=table.id,
                    name=pidx.name,
                    unique=pidx.unique,
                    columns=pidx.columns,
                )
                self.db.add(idx)

            for pfk in pt.foreign_keys:
                fk = ForeignKeyModel(
                    table_id=table.id,
                    columns=pfk.columns,
                    ref_table_name=pfk.ref_table,
                    ref_columns=pfk.ref_columns,
                    constraint_name=None,
                )
                self.db.add(fk)

            tables.append(table)

        await self.db.flush()
        return tables

    # ── Table queries ────────────────────────────────────────

    async def get_tables(self, project_id: str) -> list[Table]:
        result = await self.db.execute(
            select(Table).where(Table.project_id == project_id).order_by(Table.name)
        )
        return list(result.scalars().all())

    async def get_table_detail(self, table_id: str) -> Table | None:
        result = await self.db.execute(
            select(Table).where(Table.id == table_id)
        )
        return result.scalar_one_or_none()

    async def get_project_tables_dict(self, project_id: str) -> dict[str, Table]:
        """Return all project tables keyed by name (lowercase) for fast lookup."""
        tables = await self.get_tables(project_id)
        return {t.name.lower(): t for t in tables}

    # ── Relation persistence ─────────────────────────────────

    async def save_relations(self, project_id: str, relations: list[RelationData]) -> list[Relation]:
        # Delete existing relations for this project and re-insert
        await self.db.execute(delete(Relation).where(Relation.project_id == project_id))

        orm_relations = []
        for r in relations:
            rel = Relation(
                project_id=project_id,
                source_table_id=r.source_table_id,
                source_columns=r.source_columns,
                target_table_id=r.target_table_id,
                target_columns=r.target_columns,
                relation_type=r.relation_type,
                confidence=r.confidence,
                source=r.source,
            )
            self.db.add(rel)
            orm_relations.append(rel)

        await self.db.flush()
        return orm_relations

    async def get_relations(
        self,
        project_id: str,
        type_filter: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[Relation]:
        q = select(Relation).where(Relation.project_id == project_id)
        if type_filter:
            q = q.where(Relation.relation_type == type_filter)
        if min_confidence > 0:
            q = q.where(Relation.confidence >= min_confidence)
        q = q.order_by(Relation.confidence.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── ForeignKey queries (for detector) ────────────────────

    async def get_project_foreign_keys(self, project_id: str) -> list[ForeignKeyModel]:
        result = await self.db.execute(
            select(ForeignKeyModel)
            .join(Table, ForeignKeyModel.table_id == Table.id)
            .where(Table.project_id == project_id)
        )
        return list(result.scalars().all())

    # ── Session CRUD ─────────────────────────────────────────

    async def create_session(self, project_id: str, title: str | None = None) -> ConversationSession:
        session = ConversationSession(project_id=project_id, title=title)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: str) -> ConversationSession | None:
        result = await self.db.execute(
            select(ConversationSession).where(ConversationSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_project_sessions(self, project_id: str) -> list[ConversationSession]:
        result = await self.db.execute(
            select(ConversationSession)
            .where(ConversationSession.project_id == project_id)
            .order_by(ConversationSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def delete_session(self, session_id: str) -> bool:
        result = await self.db.execute(
            delete(ConversationSession).where(ConversationSession.id == session_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ── Message CRUD ─────────────────────────────────────────

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list | None = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(session_id=session_id, role=role, content=content, sources=sources)
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def get_messages(self, session_id: str, limit: int = 20) -> list[ConversationMessage]:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Cache CRUD ───────────────────────────────────────────

    async def get_cached(self, cache_key: str) -> dict | None:
        from datetime import datetime, timezone

        result = await self.db.execute(
            select(AICache).where(AICache.cache_key == cache_key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if row.expires_at < now:
            return None
        return row.response

    async def set_cache(
        self,
        cache_key: str,
        prompt_hash: str,
        schema_hash: str,
        response: dict,
        ttl_hours: int = 24,
    ) -> None:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        row = AICache(
            cache_key=cache_key,
            prompt_hash=prompt_hash,
            schema_hash=schema_hash,
            response=response,
            created_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        )
        self.db.add(row)
        await self.db.flush()

    async def clear_all_cache(self) -> int:
        result = await self.db.execute(delete(AICache))
        await self.db.flush()
        return result.rowcount

    async def delete_expired_cache(self) -> int:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self.db.execute(
            delete(AICache).where(AICache.expires_at < now)
        )
        await self.db.flush()
        return result.rowcount

    # ── Doc CRUD ─────────────────────────────────────────────

    async def create_doc(
        self,
        project_id: str,
        doc_type: str,
        title: str,
        content: str,
        ai_enhanced: bool = False,
    ) -> GeneratedDoc:
        doc = GeneratedDoc(
            project_id=project_id,
            doc_type=doc_type,
            title=title,
            content=content,
            ai_enhanced=ai_enhanced,
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def list_docs(self, project_id: str) -> list[GeneratedDoc]:
        result = await self.db.execute(
            select(GeneratedDoc)
            .where(GeneratedDoc.project_id == project_id)
            .order_by(GeneratedDoc.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_doc(self, doc_id: str) -> GeneratedDoc | None:
        result = await self.db.execute(
            select(GeneratedDoc).where(GeneratedDoc.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def delete_doc(self, doc_id: str) -> bool:
        result = await self.db.execute(
            delete(GeneratedDoc).where(GeneratedDoc.id == doc_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ── Version CRUD ──────────────────────────────────────────

    async def create_version(self, project_id: str, version_tag: str | None, file_hash: str, parse_result: dict) -> ProjectVersion:
        if version_tag is None:
            from datetime import datetime, timezone

            today = datetime.now(timezone.utc).strftime("%Y%m%d")
            count_q = select(func.count(ProjectVersion.id)).where(
                ProjectVersion.project_id == project_id,
                ProjectVersion.version_tag.like(f"{today}-%"),
            )
            count = (await self.db.execute(count_q)).scalar() or 0
            version_tag = f"{today}-{count + 1}"

        version = ProjectVersion(
            project_id=project_id,
            version_tag=version_tag,
            file_hash=file_hash,
            parse_result=parse_result,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def list_versions(self, project_id: str) -> list[ProjectVersion]:
        result = await self.db.execute(
            select(ProjectVersion)
            .where(ProjectVersion.project_id == project_id)
            .order_by(ProjectVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, version_id: str) -> ProjectVersion | None:
        result = await self.db.execute(
            select(ProjectVersion).where(ProjectVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def delete_version(self, version_id: str) -> bool:
        result = await self.db.execute(
            delete(ProjectVersion).where(ProjectVersion.id == version_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ── Diff CRUD ─────────────────────────────────────────────

    async def create_diff(self, project_id: str, old_version_id: str, new_version_id: str, diff_data: dict, summary: str | None = None, breaking_changes: bool = False) -> SchemaDiff:
        diff = SchemaDiff(
            project_id=project_id,
            old_version_id=old_version_id,
            new_version_id=new_version_id,
            diff_data=diff_data,
            summary=summary,
            breaking_changes=breaking_changes,
        )
        self.db.add(diff)
        await self.db.flush()
        return diff

    async def get_diff(self, diff_id: str) -> SchemaDiff | None:
        result = await self.db.execute(
            select(SchemaDiff).where(SchemaDiff.id == diff_id)
        )
        return result.scalar_one_or_none()

    async def list_diffs(self, project_id: str) -> list[SchemaDiff]:
        result = await self.db.execute(
            select(SchemaDiff)
            .where(SchemaDiff.project_id == project_id)
            .order_by(SchemaDiff.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_diff_summary(self, diff_id: str, summary: str) -> None:
        await self.db.execute(
            update(SchemaDiff).where(SchemaDiff.id == diff_id).values(summary=summary)
        )
        await self.db.flush()
