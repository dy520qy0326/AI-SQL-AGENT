import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import Repository

logger = logging.getLogger(__name__)


async def generate_markdown(
    project_id: str,
    db: AsyncSession,
    ai_enhance: bool = False,
) -> str:
    """Generate a Markdown data dictionary for a project."""
    repo = Repository(db)
    project_info = await repo.get_project(project_id)
    if project_info is None:
        raise ValueError(f"Project {project_id} not found")

    tables = await repo.get_tables(project_id)
    relations = await repo.get_relations(project_id)

    project_name = project_info["name"]
    dialect = project_info.get("dialect", "")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # AI-enhanced sections (initially empty, filled below if requested)
    ai_summary = ""
    ai_table_descriptions: dict[str, str] = {}
    ai_column_comments: dict[tuple[str, str], str] = {}

    if ai_enhance:
        from app.ai.service import (
            complete_comments,
            generate_project_summary,
            generate_table_descriptions,
        )

        # Generate project summary (fault-tolerant)
        try:
            ai_summary = await generate_project_summary(project_id, db)
        except Exception as e:
            logger.warning("AI project summary failed (non-fatal): %s", e)

        # Generate table descriptions (fault-tolerant)
        try:
            td_result = await generate_table_descriptions(project_id, db)
            # Re-fetch tables to get updated comments
            tables = await repo.get_tables(project_id)
            for t in tables:
                if t.comment and "AI Generated" in t.comment:
                    ai_table_descriptions[t.name.lower()] = t.comment
        except Exception as e:
            logger.warning("AI table descriptions failed (non-fatal): %s", e)

        # Generate column comments (fault-tolerant)
        try:
            cc_result = await complete_comments(project_id, db)
            # Re-fetch tables to get updated comments
            tables = await repo.get_tables(project_id)
            for t in tables:
                for c in t.columns:
                    if c.comment and "AI Generated" in c.comment:
                        ai_column_comments[(t.name.lower(), c.name.lower())] = c.comment
        except Exception as e:
            logger.warning("AI column comments failed (non-fatal): %s", e)

    # Build document
    lines = []

    # Title
    lines.append(f"# 数据字典 - {project_name}")
    lines.append("")
    lines.append(f"> 生成时间: {now}")
    lines.append(f"> 数据库方言: {dialect}")
    lines.append(f"> 表总数: {len(tables)}")
    lines.append(f"> 关系总数: {len(relations)}")
    if ai_enhance:
        lines.append("> AI 增强: 是")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 1: Project Overview
    lines.append("## 一、项目概览")
    lines.append("")
    if ai_summary:
        lines.append(ai_summary)
        lines.append("")
        lines.append("*（以上概览由 AI 自动生成）*")
    else:
        lines.append("（无描述）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 2: Table Details
    lines.append("## 二、表结构详情")
    lines.append("")

    # Pre-compute FK columns per table for FK marking
    fk_cols_by_table: dict[str, set[str]] = {}
    for t in tables:
        fk_cols = set()
        for fk in t.foreign_keys:
            fk_cols.update(fk.columns)
        fk_cols_by_table[t.id] = fk_cols

    for i, t in enumerate(tables, 1):
        schema_prefix = f"`{t.schema_name}.`" if t.schema_name else ""
        lines.append(f"### 2.{i} {t.name} ({schema_prefix}{t.name})")
        lines.append("")

        # Table description
        tname_lower = t.name.lower()
        if tname_lower in ai_table_descriptions:
            lines.append(f"*{ai_table_descriptions[tname_lower]}*")
        elif t.comment:
            desc = t.comment.replace(" [AI Generated]", "")
            lines.append(f"*{desc}*")
        lines.append("")

        # Columns table
        lines.append("| # | 字段名 | 类型 | NULL | PK | 默认值 | 说明 |")
        lines.append("|---|--------|------|------|----|--------|------|")

        fk_set = fk_cols_by_table.get(t.id, set())
        for ci, c in enumerate(t.columns, 1):
            pk = "✅" if c.is_primary_key else ""
            fk_mark = "FK" if c.name in fk_set else ""
            pkfk = f"{pk} {fk_mark}".strip()
            nl = "YES" if c.nullable else "NO"
            default = c.default_value or ""

            # Comment: prefer AI comment, then original comment
            comment = ""
            key = (t.name.lower(), c.name.lower())
            if key in ai_column_comments:
                comment = ai_column_comments[key]
            elif c.comment:
                comment = c.comment

            lines.append(f"| {ci} | {c.name} | {c.data_type} | {nl} | {pkfk} | {default} | {comment} |")
        lines.append("")

        # Indexes
        if t.indexes:
            lines.append("**索引：**")
            lines.append("")
            lines.append("| 索引名 | 类型 | 字段 |")
            lines.append("|--------|------|------|")
            for idx in t.indexes:
                idx_type = "UNIQUE" if idx.unique else "INDEX"
                cols = ", ".join(idx.columns)
                lines.append(f"| {idx.name} | {idx_type} | {cols} |")
            lines.append("")

        # Foreign Keys
        if t.foreign_keys:
            lines.append("**外键：**")
            lines.append("")
            lines.append("| 字段 | 引用表 | 引用字段 | 约束名 |")
            lines.append("|------|--------|---------|--------|")
            for fk in t.foreign_keys:
                src_cols = ", ".join(fk.columns)
                ref_cols = ", ".join(fk.ref_columns)
                constraint = fk.constraint_name or ""
                lines.append(f"| {src_cols} | {fk.ref_table_name} | {ref_cols} | {constraint} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Section 3: Relationships
    lines.append("## 三、关联关系")
    lines.append("")

    if relations:
        lines.append("| 来源表 | 来源字段 | 目标表 | 目标字段 | 类型 | 置信度 | 来源 |")
        lines.append("|--------|---------|--------|---------|------|--------|------|")

        id_to_name = {t.id: t.name for t in tables}
        for r in relations:
            src_name = id_to_name.get(r.source_table_id, "?")
            tgt_name = id_to_name.get(r.target_table_id, "?")
            src_cols = ", ".join(r.source_columns)
            tgt_cols = ", ".join(r.target_columns)
            source = r.source or ""
            if len(source) > 60:
                source = source[:57] + "..."
            lines.append(
                f"| {src_name} | {src_cols} | {tgt_name} | {tgt_cols} | {r.relation_type} | "
                f"{r.confidence:.2f} | {source} |"
            )
    else:
        lines.append("（无关联关系）")

    lines.append("")

    return "\n".join(lines)
