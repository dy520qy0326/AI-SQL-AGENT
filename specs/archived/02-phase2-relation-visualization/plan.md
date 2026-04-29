---
name: 02-phase2-relation-visualization
title: Phase 2 — 技术实施方案
status: REVIEWED
created: 2026-04-29
---

## 架构影响分析

### 新增模块

```
backend/app/
├── db/
│   ├── __init__.py
│   ├── engine.py          # SQLAlchemy 异步引擎 + session factory
│   └── models.py          # ORM 模型（Project, Table, Column, Index, ForeignKey, Relation）
├── store/
│   ├── __init__.py
│   └── repository.py      # 数据访问层（CRUD 操作）
├── detector/
│   ├── __init__.py
│   └── relation.py        # 关系检测服务（规则链）
├── viz/
│   ├── __init__.py
│   ├── graph.py           # graph 数据转换
│   └── mermaid.py         # Mermaid ER 语法生成
├── api/
│   ├── __init__.py
│   ├── projects.py        # /api/projects 路由
│   ├── tables.py          # /api/projects/{id}/tables 路由
│   ├── relations.py       # /api/projects/{id}/relations 路由
│   └── graph.py           # /api/projects/{id}/graph, /mermaid 路由
├── schemas/
│   ├── __init__.py
│   ├── project.py         # 请求/响应 Schema
│   ├── table.py
│   ├── relation.py
│   └── graph.py
```

### 与 Phase 1 的关系

- Phase 1 的 `app/parser/` 模块保持不变，作为解析引擎被 Store 的上传流程调用
- `ParseResult` → Store 写入的映射在 repository 层完成
- 解析器输出的 `ForeignKey` 中 `ref_table` 是字符串，Store 写入时需要解析为 `table_id`（在全部表写入后二次匹配）

### 不涉及的部分

- 前端 React 项目（`src/`）— 不创建、不修改
- AI 服务模块 — Phase 3
- 文档生成 — Phase 3
- 版本对比 — Phase 4

## 实现路径

### Task 1: 数据库基础设施

**目标**：搭建 SQLAlchemy 异步引擎和 ORM 模型

- 安装依赖：`sqlalchemy[asyncio]`、`aiosqlite` 注入到 fastapi venv
- 创建 `app/db/engine.py`：异步 SQLite 引擎（文件路径 `backend/data/metadata.db`），session factory
- 创建 `app/db/models.py`：6 个 ORM 模型（Project, Table, Column, Index, ForeignKey, Relation），使用 UUID PK
- 创建 `app/main.py` 启动事件：自动 `create_all` 建表、自动创建 `backend/data/` 目录
- Scheme 的 `__init__.py` 中暴露 `get_db` 依赖生成器

**涉及文件**：
- `backend/app/db/__init__.py`（新建）
- `backend/app/db/engine.py`（新建）
- `backend/app/db/models.py`（新建）
- `backend/app/main.py`（修改 — 添加 lifespan 事件）
- `backend/requirements.txt`（更新 — 添加依赖）

**验收**：数据库文件创建成功，表结构正确；`get_db` 依赖注入可用

---

### Task 2: 元数据存储层（Repository）

**目标**：实现所有 CRUD 数据访问操作

- `create_project(name, description, dialect)` → Project
- `get_project(project_id)` → Project + table_count + relation_count
- `list_projects(page, size)` → (projects, total)
- `delete_project(project_id)` → 级联删除所有关联数据
- `save_parse_result(project_id, parse_result)` → 事务内批量写入 Table/Column/Index/ForeignKey
- `get_tables(project_id)` → List[Table]
- `get_table_detail(table_id)` → Table + columns + indexes + foreign_keys
- `save_relations(project_id, relations)` → 批量 upsert Relation（按 source_table_id + target_table_id + source_columns 去重）
- `get_relations(project_id, type_filter, min_confidence)` → List[Relation]

**关键逻辑**：
- `save_parse_result` 中，ForeignKey 的 `ref_table_name` 暂时存储字符串；全部表写入后，在 detector 阶段解析为 table_id
- 事务管理：使用 `async with session.begin()` 保证解析写入的原子性

**涉及文件**：
- `backend/app/store/__init__.py`（新建）
- `backend/app/store/repository.py`（新建）

**验收**：所有 CRUD 方法单元测试通过，事务回滚验证通过

---

### Task 3: API 路由 — 项目与上传

**目标**：实现 Project CRUD + DDL 上传解析 API

- `POST /api/projects` — 创建项目
- `GET /api/projects` — 项目列表（分页）
- `GET /api/projects/{id}` — 项目详情 + 统计
- `DELETE /api/projects/{id}` — 删除项目
- `POST /api/projects/{id}/upload` — 接收 SQL 文本，调用 Parser → Repository 写入

**关键逻辑**：
- upload 端点接收 `{"sql": "CREATE TABLE ..."}` JSON body
- 调用 `app/parser/` 的解析器解析 SQL
- 调用 `save_parse_result` 写入
- 调用 Relation Detector 执行关系检测
- 调用 `save_relations` 写入关系
- 全部在一个请求内完成，解析失败返回 422

**涉及文件**：
- `backend/app/schemas/project.py`（新建）
- `backend/app/api/projects.py`（新建）
- `backend/app/main.py`（修改 — 注册路由）

**验收**：API 集成测试通过；上传标准 DDL → 查询表列表 → 数据完整

---

### Task 4: 关系检测服务

**目标**：实现规则链式关系推断引擎

规则执行顺序：
1. **显式外键转换**：读取 ForeignKey 记录，匹配 ref_table_name → Table，生成 FOREIGN_KEY Relation（confidence=1.0）
2. **`_id` 后缀推断**：扫描所有 `_id` 结尾字段，提取前缀（如 `user_id` → `user`），与项目中其他表名匹配（精确 + 复数模糊）
3. **同名字段推断**：两张不同表中同名、同类型的非主键字段
4. **N:M 中间表标记**：字段数 ≤ 5、恰好 2 个 ForeignKey 的表，在 Relation 的 source 字段中标注 `"N:M intermediate table"`
5. **去重合并**：同一对 (source_table, source_columns, target_table, target_columns) 只保留最高置信度

**英文复数处理**（轻量，不引入 NLP 库）：
- 实现简单的反向单数化：`users` → `user`、`categories` → `category`、`boxes` → `box`
- 规则覆盖：`ies` → `y`、`es` → ` `、`s` → ` `

**涉及文件**：
- `backend/app/detector/__init__.py`（新建）
- `backend/app/detector/relation.py`（新建）

**验收**：单元测试覆盖率 > 90%；标准测试集（20 张表 DDL）显式 FK 全检出 + 隐式推断准确率 > 90%

---

### Task 5: API 路由 — 表查询与关系查询

**目标**：实现表和关系的查询 API

- `GET /api/projects/{id}/tables` — 表列表
- `GET /api/projects/{id}/tables/{tid}` — 表详情
- `GET /api/projects/{id}/relations` — 关系列表（支持 `?type=FOREIGN_KEY&min_confidence=0.6` 筛选）

**涉及文件**：
- `backend/app/schemas/table.py`（新建）
- `backend/app/schemas/relation.py`（新建）
- `backend/app/api/tables.py`（新建）
- `backend/app/api/relations.py`（新建）
- `backend/app/main.py`（修改 — 注册路由）

**验收**：API 返回数据结构正确；筛选参数生效

---

### Task 6: 可视化数据接口

**目标**：实现 graph 和 mermaid 端点

**Graph 端点** (`GET /api/projects/{id}/graph`)：
- 输出格式（前端 vis-network / D3.js 直接消费）：
```json
{
  "nodes": [
    {
      "id": "table-uuid",
      "label": "users",
      "schema": "public",
      "column_count": 5,
      "columns": [
        {"name": "id", "type": "int", "pk": true, "fk": false},
        {"name": "email", "type": "varchar", "pk": false, "fk": false}
      ]
    }
  ],
  "edges": [
    {
      "id": "relation-uuid",
      "from": "orders-uuid",
      "to": "users-uuid",
      "label": "user_id → id",
      "type": "FOREIGN_KEY",
      "confidence": 1.0,
      "dashes": false
    }
  ]
}
```
- `dashes: true` 用于 INFERRED 类型，前端据此渲染虚线
- 查询参数支持 `?min_confidence=0.6&type=FOREIGN_KEY`

**Mermaid 端点** (`GET /api/projects/{id}/mermaid`)：
- 返回 `text/plain` Mermaid ER 图语法
- 外键关系用 `||--o{` 表示
- 推断关系在 label 中标注 `[inferred, 0.85]`

**涉及文件**：
- `backend/app/schemas/graph.py`（新建）
- `backend/app/viz/__init__.py`（新建）
- `backend/app/viz/graph.py`（新建）
- `backend/app/viz/mermaid.py`（新建）
- `backend/app/api/graph.py`（新建）
- `backend/app/main.py`（修改 — 注册路由）

**验收**：graph 输出可被 vis-network 解析；mermaid 输出可在 Mermaid Live Editor 正确渲染

---

### Task 7: 集成测试与验证

**目标**：端到端测试，覆盖完整流程

- 准备标准测试 DDL（20 张表，包含显式 FK、`_id` 命名、同名字段、中间表）
- 测试完整流程：创建项目 → 上传 DDL → 查询表列表 → 查询关系 → 获取 graph → 导出 mermaid
- 测试错误场景：空 SQL、语法错误 SQL、项目不存在
- 性能测试：200 张表关系推断 < 2s

**涉及文件**：
- `backend/tests/test_store.py`（新建）
- `backend/tests/test_detector.py`（新建）
- `backend/tests/test_api_projects.py`（新建）
- `backend/tests/test_api_graph.py`（新建）
- `backend/tests/fixtures/sample_20_tables.sql`（新建）

**验收**：所有测试通过；测试覆盖率 > 85%

## 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| aiosqlite 并发限制 | SQLite 不支持高并发写 | upload 端点串行化，冲突返回 409；生产环境迁移至 PostgreSQL |
| ForeignKey ref_table 字符串 → UUID 映射 | 表写入后才可解析 | 两阶段处理：先写入所有表，再解析 FK → Relation |
| 自引用外键 | 同一张表同时是 source 和 target | Repository 需处理 source_table_id == target_table_id 的情况 |
| 英文复数规则覆盖不全 | 部分表名匹配失败 | 规则覆盖主流模式（s/es/ies）；不引入额外依赖；边界 case 由后续 AI 补全覆盖 |

## 工作量估算

| Task | 估算时间 |
|------|---------|
| Task 1: 数据库基础设施 | 小 |
| Task 2: Repository 层 | 中 |
| Task 3: 项目与上传 API | 中 |
| Task 4: 关系检测服务 | 中 |
| Task 5: 表与关系查询 API | 小 |
| Task 6: 可视化数据接口 | 小 |
| Task 7: 集成测试 | 中 |

## 依赖安装

```bash
pipx inject fastapi "sqlalchemy[asyncio]" aiosqlite
```
