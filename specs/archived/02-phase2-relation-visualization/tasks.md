---
name: 02-phase2-relation-visualization
title: Phase 2 — 任务分解
status: REVIEWED
created: 2026-04-29
---

## 依赖关系

```
Task 1 (数据库) ──→ Task 2 (Repository) ──→ Task 3 (上传API) ──→ Task 5 (查询API)
                        │                         │                    │
                        └─────────────┬───────────┘                    │
                                      └──→ Task 4 (关系检测) ←─────────┘
                                                │
                                                └──→ Task 6 (可视化)
                                                          │
                                                          └──→ Task 7 (集成测试)
```

Task 2/3/4 是核心链路，需严格按序执行。Task 5/6 可部分并行。

---

## Task 1: 数据库基础设施

**依赖**：无（Phase 1 解析器已就绪）

**交付标准**：
- [ ] `app/db/engine.py`：异步 SQLite 引擎 + `async_sessionmaker` + `get_db` 依赖生成器
- [ ] `app/db/models.py`：6 个 ORM 模型
  - `Project`（id, name, description, dialect, created_at, updated_at）
  - `Table`（id, project_id FK, schema_name, name, comment, created_at）
  - `Column`（id, table_id FK, name, ordinal_position, data_type, length, nullable, default_value, is_primary_key, comment）
  - `Index`（id, table_id FK, name, unique, columns JSON）
  - `ForeignKey`（id, table_id FK, columns JSON, ref_table_name, ref_columns JSON, constraint_name）
  - `Relation`（id, project_id FK, source_table_id FK, target_table_id FK, source_columns JSON, target_columns JSON, relation_type enum, confidence, source）
- [ ] `app/main.py` 添加 lifespan 事件：启动时 `create_all` + 自动创建 `backend/data/` 目录
- [ ] 安装依赖：`pipx inject fastapi "sqlalchemy[asyncio]" aiosqlite`

**验收**：
1. 启动应用，`backend/data/metadata.db` 自动创建
2. 数据库 6 张表结构正确（通过 sqlite3 `.schema` 验证）
3. `get_db` 依赖注入可正常 yield session

---

## Task 2: 元数据存储层（Repository）

**依赖**：Task 1

**交付标准**：
- [ ] `create_project(name, description, dialect)` → Project
- [ ] `get_project(project_id)` → Project + table_count + relation_count
- [ ] `list_projects(page, size)` → (projects, total)，按 created_at 降序
- [ ] `delete_project(project_id)` → 级联删除 Table/Column/Index/ForeignKey/Relation
- [ ] `save_parse_result(project_id, parse_result: ParseResult)` → 事务内批量写入
- [ ] `get_tables(project_id)` → List[Table]（不含 columns 详情）
- [ ] `get_table_detail(table_id)` → Table + columns + indexes + foreign_keys
- [ ] `save_relations(project_id, relations)` → upsert（按 source_table_id + target_table_id + source_columns 去重）
- [ ] `get_relations(project_id, type_filter, min_confidence)` → List[Relation]
- [ ] `get_project_tables_dict(project_id)` → Dict[str, Table]（供 Detector 使用，按表名索引）

**关键实现细节**：
- `save_parse_result` 内使用 `session.begin()` 保证原子性
- ForeignKey 的 `ref_table_name` 暂存字符串（目标表可能尚未写入）
- upsert 逻辑：先 delete 匹配的旧 Relation，再 insert 新的

**验收**：
1. 单元测试覆盖每个 CRUD 方法
2. 事务回滚测试：写入一半抛异常，数据库无脏数据
3. 级联删除测试：删除 Project → 所有关联数据清除

---

## Task 3: API 路由 — 项目与上传

**依赖**：Task 2

**交付标准**：
- [ ] `app/schemas/project.py`：请求/响应 Pydantic Schema
  - `ProjectCreate(name, description?)` 
  - `ProjectResponse(id, name, description, dialect, table_count, relation_count, created_at)`
  - `ProjectListResponse(items, total, page, size)`
  - `UploadRequest(sql_content: str)`
- [ ] `app/api/projects.py`：4 个端点
  - `POST /api/projects` → 201
  - `GET /api/projects` → 200（query: page, size）
  - `GET /api/projects/{id}` → 200 / 404
  - `DELETE /api/projects/{id}` → 204 / 404
  - `POST /api/projects/{id}/upload` → 200（调用 Parser → Repository → Detector）
- [ ] `app/main.py` 注册 projects router

**upload 端点处理流程**：
```
1. 验证项目存在
2. 调用 parser 解析 SQL
3. 如果 parse_result.tables 为空且 errors 非空 → 返回 422
4. 调用 save_parse_result 事务写入
5. 调用 detector.detect_relations(project_id) 执行关系检测
6. 调用 save_relations 写入关系
7. 返回 {tables_count, relations_count, errors}
```

**验收**：
1. 创建项目 → 返回 201 + 正确字段
2. 上传标准 DDL → 表数据完整入库
3. 上传含语法错误的 DDL → 返回 422 + 错误列表
4. 删除项目 → 级联清除

---

## Task 4: 关系检测服务

**依赖**：Task 2（需要 Repository 的查询方法）

**交付标准**：
`app/detector/relation.py` 实现 `RelationDetector` 类，入口方法：

```python
async def detect(project_id: str, db: AsyncSession) -> list[RelationCreate]:
```

内部规则链按序执行：

### 4a. 显式外键转换
- 读取项目所有 ForeignKey 记录
- 遍历每条 FK，用 `ref_table_name` 在 `get_project_tables_dict()` 中匹配目标表
- 匹配成功 → 生成 FOREIGN_KEY Relation（confidence=1.0, source="DDL explicit FK: {constraint_name}")
- 匹配失败（目标表不在项目中）→ 跳过，记录 warning 日志

### 4b. `_id` 后缀推断
- 扫描所有以 `_id` 结尾的字段
- 提取前缀（`user_id` → `user`），与项目表名做匹配
- 反向单数化表名：`users` → `user`、`categories` → `category`、`boxes` → `box`
- 精确匹配（`user` == `user`）→ confidence=0.85
- 单复数匹配（`user` → `users` 反向）→ confidence=0.70
- 已存在 FOREIGN_KEY Relation 的字段对 → 跳过

### 4c. 同名字段推断
- 遍历所有非主键字段，按 (name, data_type) 分组
- 同一分组内，跨表配对生成 INFERRED Relation（confidence=0.60）
- 排除已存在的 Relation

### 4d. N:M 中间表识别
- 识别条件：表字段数 ≤ 5 且恰好有 2 条 ForeignKey
- 在已生成的 Relation 中，对涉及中间表的 Relation 追加 source 说明 `" [N:M intermediate]"`
- 不生成新的 Relation，仅标记

### 4e. 去重
- 按 (source_table_id, tuple(sorted(source_columns)), target_table_id, tuple(sorted(target_columns))) 去重
- 保留 confidence 最高的一条

**复数处理函数**（内联实现，不引入新依赖）：
```python
def singularize(word: str) -> str:
    """简易反向单数化：users→user, categories→category, boxes→box"""
    if word.endswith("ies"):
        return word[:-3] + "y"
    elif word.endswith("ses") or word.endswith("xes") or word.endswith("zes") or word.endswith("ches") or word.endswith("shes"):
        return word[:-2]
    elif word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word
```

**验收**：
1. 标准测试集：显式 FK 检出率 100%
2. `_id` 推断：`user_id` → `users.id` 正确匹配（exact + plural）
3. 同名字段：两张表都有 `org_id int` → 生成 INFERRED Relation
4. N:M 中间表正确标记
5. 去重：重复关系只保留最高分一条
6. 单元测试覆盖率 > 90%

---

## Task 5: API 路由 — 表查询与关系查询

**依赖**：Task 2, Task 3（共享 schemas 和路由结构）

**交付标准**：
- [ ] `app/schemas/table.py`
  - `TableResponse(id, name, schema_name, comment, column_count, created_at)`
  - `TableDetailResponse(...columns, indexes, foreign_keys)`
- [ ] `app/schemas/relation.py`
  - `RelationResponse(id, source_table_name, source_columns, target_table_name, target_columns, relation_type, confidence, source)`
  - `RelationListResponse(items, total)`
- [ ] `app/api/tables.py`
  - `GET /api/projects/{project_id}/tables` → 表列表
  - `GET /api/projects/{project_id}/tables/{table_id}` → 表详情
- [ ] `app/api/relations.py`
  - `GET /api/projects/{project_id}/relations` → 关系列表
  - Query params: `type`（FOREIGN_KEY / INFERRED）、`min_confidence`（0.0~1.0）
- [ ] `app/main.py` 注册路由

**验收**：
1. 表列表返回正确字段，不包含 columns 详情
2. 表详情返回完整 columns + indexes + foreign_keys
3. 关系筛选：`?type=FOREIGN_KEY` 只返回显式外键
4. 关系筛选：`?min_confidence=0.8` 只返回高置信度关系

---

## Task 6: 可视化数据接口

**依赖**：Task 2, Task 5（需要 Table 和 Relation 查询能力）

**交付标准**：
- [ ] `app/schemas/graph.py`
  - `GraphNode(id, label, schema, column_count, columns: List[ColumnBrief])`
  - `ColumnBrief(name, type, pk, fk)`
  - `GraphEdge(id, from_, to, label, type, confidence, dashes)`
  - `GraphResponse(nodes, edges)`
- [ ] `app/viz/graph.py`：`build_graph(project_id, min_confidence, type_filter)` → GraphResponse
- [ ] `app/viz/mermaid.py`：`build_mermaid(project_id, min_confidence)` → str
- [ ] `app/api/graph.py`
  - `GET /api/projects/{project_id}/graph` → GraphResponse
  - `GET /api/projects/{project_id}/mermaid` → PlainTextResponse

**Mermaid 格式规范**：
```
erDiagram
  table_uuid_1["users"] {
    int id PK
    varchar name
  }
  table_uuid_2["orders"] {
    int id PK
    int user_id FK
  }
  table_uuid_1 ||--o{ table_uuid_2 : "user_id → id [FK]"
```

- 使用 `["label"]` 语法包裹表名（支持特殊字符）
- PK 列标注 `PK`，FK 列标注 `FK`
- 关系标注类型和置信度
- 自引用表使用 `}o--o{` 语法

**验收**：
1. `/graph` 返回 correct nodes + edges 结构（vis-network 可消费）
2. `/mermaid` 返回文本在 Mermaid Live Editor 中正确渲染
3. INFERRED 关系 `dashes: true`，FOREIGN_KEY 关系 `dashes: false`
4. column 中 `fk: true` 正确标记所有参与外键的字段

---

## Task 7: 集成测试与验证

**依赖**：Task 1-6 全部完成

**交付标准**：
- [ ] `backend/tests/fixtures/sample_20_tables.sql`：20 张表的标准测试 DDL
  - 包含：显式 FK（列级 + 表级）、`_id` 命名约定、同名字段、N:M 中间表、自引用、复合外键
- [ ] `backend/tests/test_store.py`：Repository CRUD 完整测试
- [ ] `backend/tests/test_detector.py`：关系检测规则链测试
- [ ] `backend/tests/test_api_projects.py`：项目 + 上传 API 集成测试
- [ ] `backend/tests/test_api_graph.py`：Graph + Mermaid 端点测试

**测试场景清单**：
1. 完整流程：创建项目 → 上传 DDL → 表列表 → 表详情 → 关系列表 → graph → mermaid
2. 空 SQL 上传 → 400
3. 全语法错误 SQL → 422
4. 不存在的项目 → 404
5. 关系筛选：type + min_confidence 组合
6. 级联删除验证
7. 重复上传同一项目（重新解析）
8. 20 张表性能：关系推断 < 2s

**验收**：
- [ ] `pytest` 全量通过
- [ ] 覆盖率 > 85%（`pytest --cov=app --cov-report=term`）
- [ ] 20 张表关系推断耗时 < 2s

---

## 执行顺序总结

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
                              ↘_Task 5/6 可部分并行
```

每完成一个 Task 暂停，等待 Review 后再继续下一个。
