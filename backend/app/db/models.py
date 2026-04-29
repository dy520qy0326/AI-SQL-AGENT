import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.engine import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    dialect: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    tables: Mapped[list["Table"]] = relationship("Table", cascade="all, delete-orphan", lazy="selectin")
    relations: Mapped[list["Relation"]] = relationship(
        "Relation", cascade="all, delete-orphan", lazy="selectin",
        foreign_keys="Relation.project_id",
    )
    sessions: Mapped[list["ConversationSession"]] = relationship(
        "ConversationSession", cascade="all, delete-orphan", lazy="selectin",
    )
    docs: Mapped[list["GeneratedDoc"]] = relationship(
        "GeneratedDoc", cascade="all, delete-orphan", lazy="selectin",
    )


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    columns: Mapped[list["Column"]] = relationship("Column", cascade="all, delete-orphan", lazy="selectin")
    indexes: Mapped[list["Index"]] = relationship("Index", cascade="all, delete-orphan", lazy="selectin")
    foreign_keys: Mapped[list["ForeignKeyModel"]] = relationship(
        "ForeignKeyModel", cascade="all, delete-orphan", lazy="selectin",
        foreign_keys="ForeignKeyModel.table_id",
    )


class Column(Base):
    __tablename__ = "columns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    table_id: Mapped[str] = mapped_column(String(36), ForeignKey("tables.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nullable: Mapped[bool] = mapped_column(default=True)
    default_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_primary_key: Mapped[bool] = mapped_column(default=False)
    comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class Index(Base):
    __tablename__ = "indexes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    table_id: Mapped[str] = mapped_column(String(36), ForeignKey("tables.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unique: Mapped[bool] = mapped_column(default=False)
    columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class ForeignKeyModel(Base):
    __tablename__ = "foreign_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    table_id: Mapped[str] = mapped_column(String(36), ForeignKey("tables.id", ondelete="CASCADE"))
    columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ref_table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ref_columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    constraint_name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Relation(Base):
    __tablename__ = "relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    source_table_id: Mapped[str] = mapped_column(String(36), ForeignKey("tables.id", ondelete="CASCADE"))
    target_table_id: Mapped[str] = mapped_column(String(36), ForeignKey("tables.id", ondelete="CASCADE"))
    source_columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    target_columns: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", cascade="all, delete-orphan", lazy="selectin",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversation_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AICache(Base):
    __tablename__ = "ai_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class GeneratedDoc(Base):
    __tablename__ = "generated_docs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"))
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False, default="markdown")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    ai_enhanced: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
