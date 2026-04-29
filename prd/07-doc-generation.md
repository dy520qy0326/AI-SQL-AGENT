# PRD: 文档自动生成模块 (Doc Generation)

## 1. 产品概述

文档自动生成模块利用项目已解析的元数据和 AI 能力，自动生成结构化、可读性强的数据库设计文档，减少人工维护数据字典的工作量。

## 2. 目标用户

- **主要用户**：后端开发、技术管理者需要产出技术文档
- **输出格式**：Markdown（核心）、PDF（增强）、PlantUML（增强）

## 3. 功能需求

### P0 — Markdown 数据字典

| 功能 | 说明 |
|------|------|
| 表总览 | 按 schema 分组的表清单，包含表名、注释、记录数（预留） |
| 字段明细 | 每张表的字段列表表格：序号、字段名、类型、是否为空、主键、默认值、注释 |
| 索引清单 | 每张表的索引列表 |
| 关系说明 | 外键关系表格：来源表、来源字段、目标表、目标字段、关系类型 |

### P1 — AI 增强文档

| 功能 | 说明 |
|------|------|
| AI 表说明 | 自动生成每张表的功能描述（"存储用户基本信息，包含登录凭证"） |
| AI 字段说明 | 对缺失注释的字段自动生成说明 |
| AI 摘要 | 生成项目整体数据模型概览（"该系统采用星型模型，核心事实表为 orders..."） |
| 设计建议 | AI 分析 schema 后给出索引优化、规范化建议（可选） |

### P2 — 多格式导出

| 功能 | 说明 |
|------|------|
| PDF 导出 | Markdown -> PDF（通过 wkhtmltopdf 或 pandoc） |
| PlantUML 导出 | 自动生成 PlantUML ER 图文本 |
| Confluence 导出 | 格式化后适配 Confluence Wiki 标记 |

## 4. 文档模板

### Markdown 模板

```markdown
# 数据字典 - {project_name}

> 生成时间: {generated_at}
> 表总数: {table_count}
> 关系总数: {relation_count}

---

## 一、项目概览

{ai_generated_summary}

---

## 二、表结构详情

### 2.1 {table_name} (`{schema}.{table_name}`)

{table_comment}

| # | 字段名 | 类型 | NULL | PK | 默认值 | 说明 |
|---|--------|------|------|----|--------|------|
| 1 | id | bigint | NO | ✅ | auto_increment | 主键 |
| 2 | name | varchar(50) | NO |    |          | 名称 |

**索引：**
| 索引名 | 类型 | 字段 |
|--------|------|------|
| idx_name | UNIQUE | name |

---

## 三、关联关系

| 来源表 | 来源字段 | 目标表 | 目标字段 | 类型 | 置信度 |
|--------|---------|--------|---------|------|--------|
| orders | user_id | users | id | FOREIGN_KEY | 1.0 |
```

## 5. 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/docs/generate-markdown | 生成 Markdown 数据字典 |
| POST | /api/projects/{id}/docs/generate-pdf | 生成 PDF 文档 |
| POST | /api/projects/{id}/docs/generate-plantuml | 生成 PlantUML |
| GET | /api/projects/{id}/docs | 查询已生成的文档列表 |
| DELETE | /api/projects/{id}/docs/{doc_id} | 删除生成的文档 |

## 6. 验收标准

- [ ] Markdown 数据字典包含所有表、字段、索引、关系信息
- [ ] 表格格式规范，在 GitHub / Typora / VSCode 中渲染正常
- [ ] AI 生成的表说明没有事实错误（不捏造不存在的字段）
- [ ] 100 张表的文档生成（不含 AI）< 3s
- [ ] PDF 导出格式整洁，不出现乱码/断页
- [ ] PlantUML 代码可被 PlantUML 服务正常渲染
- [ ] 用户可在前端一键复制 Markdown / 下载文档
