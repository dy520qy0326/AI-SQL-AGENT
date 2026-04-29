---
name: 04-phase4-version-diff
title: Phase 4 — 任务分解
status: REVIEWED
created: 2026-04-29
---

## 依赖关系

```
Task 1 (数据模型) ──→ Task 2 (Diff Engine) ──→ Task 3 (Migration + AI)
                            │                          │
                            └──→ Task 4 (API) ─────────┘
                                          │
                                          └──→ Task 5 (测试)
```

Task 2 是核心瓶颈。Task 3/4 在 Task 2 完成后可部分并行。

---

## Task 1: 数据模型 + Repository 扩展

**依赖**：无（基于 Phase 1-3 现有基础设施）

**交付标准**：
- [ ] `app/db/models.py` 新增：

  **ProjectVersion**
  - id: String(36) PK, default uuid4
  - project_id: FK → projects.id, ondelete CASCADE
  - version_tag: String(100), nullable（null 时自动生成 "YYYYMMDD-N"）
  - file_hash: String(64)
  - parse_result: JSON（完整的解析结果快照）
  - created_at: DateTime, default utcnow
  - project → relationship backref

  **SchemaDiff**
  - id: String(36) PK, default uuid4
  - project_id: FK → projects.id, ondelete CASCADE
  - old_version_id: FK → project_versions.id
  - new_version_id: FK → project_versions.id
  - diff_data: JSON
  - summary: Text, nullable
  - breaking_changes: Boolean, default False
  - created_at: DateTime, default utcnow
  - project → relationship backref

- [ ] `app/store/repository.py` 新增方法：

  **Version**
  - `create_version(project_id, version_tag, file_hash, parse_result)` → ProjectVersion
  - `list_versions(project_id)` → List[ProjectVersion]（按 created_at 降序）
  - `get_version(version_id)` → ProjectVersion | None
  - `delete_version(version_id)` → bool

  **Diff**
  - `create_diff(project_id, old_version_id, new_version_id, diff_data, summary, breaking_changes)` → SchemaDiff
  - `get_diff(diff_id)` → SchemaDiff | None
  - `list_diffs(project_id)` → List[SchemaDiff]（按 created_at 降序）
  - `update_diff_summary(diff_id, summary)` → None

- [ ] `app/schemas/version.py`：
  - `VersionCreateRequest(sql_content, version_tag=None)`
  - `VersionResponse(id, project_id, version_tag, file_hash, tables_count, created_at)`
  - `VersionListResponse(items, total)`
  - `DiffRequest(old_version_id, new_version_id)`
  - `DiffResponse(id, project_id, diff_data, summary, breaking_changes, created_at)`
  - `DiffListResponse(items, total)`

**涉及文件**：
- `backend/app/db/models.py`（修改）
- `backend/app/store/repository.py`（修改）
- `backend/app/schemas/version.py`（新建）

**验收**：
1. 启动后 project_versions 和 schema_diffs 表自动创建
2. 版本 CRUD 测试通过
3. 级联删除：删 Project → 级联删除关联 Versions 和 Diffs

---

## Task 2: Diff Engine — 核心差异检测

**依赖**：Task 1

**交付标准**：
- [ ] `app/diff/engine.py`：

  **核心函数**
  - `compute_diff(old_tables: list[dict], new_tables: list[dict])` → `DiffResult` dataclass
  
  **DiffResult 结构**
  ```python
  @dataclass
  class DiffResult:
      tables_added: list[dict]       # 新增的表（完整 schema）
      tables_removed: list[dict]     # 删除的表
      tables_renamed: list[dict]     # 重名名: [{old_name, new_name, similarity}]
      fields_added: list[dict]       # [{table, field, definition}]
      fields_removed: list[dict]     # [{table, field, definition}]
      fields_modified: list[dict]    # [{table, field, before, after}]
      indexes_added: list[dict]      # [{table, index}]
      indexes_removed: list[dict]    # [{table, index}]
      relations_added: list[dict]    # [{table, relation}]
      relations_removed: list[dict]  # [{table, relation}]
      breaking_changes: bool
      breaking_details: list[str]
      summary_stats: dict            # {tables: +/-N, fields: +/-M, ...}
  ```

  **表级匹配算法**
  - 用表名做精确匹配 → 候选匹配集
  - 旧版中未匹配的表名 → 遍历新版中未匹配的表名，计算编辑距离（Levenshtein）和字段集 Jaccard 相似度
  - 编辑距离 ≤ 3 且 字段重叠度 ≥ 0.8 → 判定为重命名
  - 仍无法匹配的 → 新增/删除

  **字段级对比（同表内）**
  - 字段名精确匹配 → 对比属性（data_type, length, nullable, default_value）
  - 属性不同 → fields_modified（记录 before/after）
  - 未匹配字段：
    - 在新版表字段集合中但不在旧版 → fields_added
    - 在旧版表字段集合中但不在新版 → fields_removed
  - 字段重名检测：对"已删除+已新增"的字段组合，同一位置 ±2 + 类型一致 → 标记为重命名候选

  **索引对比**
  - 索引名精确匹配 → 跳过
  - 索引名存在于旧版但不存在于新版 → indexes_removed
  - 索引名存在于新版但不存在于旧版 → indexes_added

  **关系对比**
  - 用 (source_columns, target_columns, ref_table) 三元组做匹配
  - 旧版有新版无 → relations_removed
  - 新版有旧版无 → relations_added

  **破坏性变更判定**
  - 类型缩窄（按优先级排序：bigint→int, varchar(255)→varchar(100), decimal(10,2)→decimal(8,2)）
  - NOT NULL → NULL
  - 长度缩短
  - 删除字段/表/索引/关系
  - 以上任一成立 → breaking_changes = True

**涉及文件**：
- `backend/app/diff/__init__.py`（新建）
- `backend/app/diff/engine.py`（新建）

**验收**：
1. 新增表 + 删除表各一张 → 差异列表正确
2. 字段类型 int → bigint → 标记为"类型变更"
3. 字段改名（同一位置 + 同类型）→ 不误报为删除+新增
4. 完全相同 → diff_data 为空
5. 破坏性变更正确标记

---

## Task 3: Migration 脚本生成 + AI 摘要

**依赖**：Task 2

**交付标准**：
- [ ] `app/diff/migration.py`：
  - `generate_alter_scripts(diff_data: dict, dialect: str)` → str
  - 按表组织，逐变更生成 SQL：
    - **新增表**：`CREATE TABLE {name} (...)`
    - **删除表**：`DROP TABLE IF EXISTS {name};`
    - **新增字段**：`ALTER TABLE {t} ADD COLUMN {col} {type} ...;`
    - **删除字段**：`ALTER TABLE {t} DROP COLUMN {col};`
    - **修改字段 MySQL**：`ALTER TABLE {t} MODIFY COLUMN {col} {new_type} ...;`
    - **修改字段 PostgreSQL**：`ALTER TABLE {t} ALTER COLUMN {col} TYPE {new_type};`
    - **新增索引**：`CREATE [UNIQUE] INDEX {name} ON {t}({cols});`
    - **删除索引**：`DROP INDEX {name};`（MySQL）/ `DROP INDEX IF EXISTS {name};`（PostgreSQL）
  - 按 dialect 输出对应语法
  - 在脚本头部添加注释：`-- Migration generated by AI SQL Agent`
  - 添加 `-- --- destructive changes ---` 注释标记破坏性变更

- [ ] AI 变更摘要（在 API 层调用，或直接在 engine.py 中提供函数）：
  - 复用 `app/ai/client.py` 的 `ai_client.complete()`
  - Prompt 传入结构化的 diff_data JSON
  - 返回 3-5 句话的变更摘要
  - 调用时通过 `asyncio.to_thread` 避免阻塞

**涉及文件**：
- `backend/app/diff/migration.py`（新建）

**验收**：
1. MySQL 模式下 ALTER TABLE 使用 MODIFY COLUMN 语法
2. PostgreSQL 模式下 ALTER TABLE 使用 ALTER COLUMN TYPE 语法
3. 新增表生成完整的 CREATE TABLE
4. 破坏性变更在脚本中有注释标记
5. AI 摘要不包含不存在的变更

---

## Task 4: API 路由 + 集成

**依赖**：Task 2, Task 3

**交付标准**：
- [ ] `app/api/diff.py`：

  **版本管理**
  - `POST /api/projects/{project_id}/versions`
    - 接收 `{sql_content, version_tag?}`
    - 调用 Parser 解析 SQL
    - 计算 file_hash（SHA256）
    - 保存 ProjectVersion（parse_result 为完整解析结果 JSON）
    - 返回 201 + VersionResponse
  - `GET /api/projects/{project_id}/versions`
    - 返回版本列表
  - `DELETE /api/projects/{project_id}/versions/{version_id}`
    - 删除指定版本

  **差异对比**
  - `POST /api/projects/{project_id}/diff`
    - 接收 `{old_version_id, new_version_id}`
    - 从 DB 读取两个版本的 parse_result
    - 调用 `engine.compute_diff()` 计算差异
    - 保存 SchemaDiff
    - 返回 201 + DiffResponse
  - `GET /api/projects/{project_id}/diff/{diff_id}`
    - 返回差异详情
  - `GET /api/projects/{project_id}/diffs`
    - 项目的历史对比列表

  **增强功能**
  - `POST /api/projects/{project_id}/diff/{diff_id}/ai-summary`
    - 调用 AI 生成变更摘要
    - 更新 SchemaDiff.summary
    - 返回 summary 文本
    - 需要 `AI_ENABLED=true`，否则返回 503
  - `POST /api/projects/{project_id}/diff/{diff_id}/migration`
    - 获取项目 dialect
    - 调用 `migration.generate_alter_scripts()`
    - 返回 `PlainTextResponse`（`text/x-sql`）

  **错误处理**
  - Project 不存在 → 404
  - Version 不存在 → 404
  - 两个版本相同 → diff_data 全空
  - AI 不可用 → migration 不受影响，仅 ai-summary 返回 503

- [ ] `app/main.py`：
  - 导入并注册 diff_router
  - 验证 lifespan 中自动建表（新增 ProjectVersion、SchemaDiff）

**涉及文件**：
- `backend/app/api/diff.py`（新建）
- `backend/app/schemas/version.py`（新建）
- `backend/app/main.py`（修改）

**验收**：
1. 创建版本 → 列表可查 → 对比 → 查看差异 → 生成迁移脚本，全链路正常
2. 两个相同版本对比 → diff_data 为空
3. AI 摘要端点正确返回
4. migration 端点返回有效 SQL
5. 删除项目后版本和差异级联删除

---

## Task 5: 测试

**依赖**：Task 2, Task 3, Task 4

**交付标准**：
- [ ] `backend/tests/fixtures/sample_ecommerce_v2.sql`：
  - 在 `sample_ecommerce.sql` 基础上修改：
    - 删除 1 张表（如 logistics）
    - 新增 1 张表（如 coupons）
    - 修改 1 个字段类型（如 orders.total decimal(10,2) → decimal(12,2)）
    - 新增 1 个字段（如 orders.coupon_id）
    - 删除 1 个字段（如 products.stock_quantity）
    - 修改 1 个字段 NULL 属性
    - 新增 1 个索引
    - 重命名 1 张表

- [ ] `backend/tests/test_diff_engine.py`：
  - 测试表级差异：新增/删除/重命名
  - 测试字段级差异：新增/删除/类型变更/NULL/默认值
  - 测试字段重命名检测（不误报为删除+新增）
  - 测试索引差异
  - 测试关系差异
  - 测试完全相同 → 空 diff
  - 测试破坏性变更判定（类型缩窄、NOT NULL→NULL、删除字段/表）
  - 测试空表 vs 非空表

- [ ] `backend/tests/test_diff_migration.py`：
  - 测试 MySQL ALTER TABLE 语法
  - 测试 PostgreSQL ALTER TABLE 语法
  - 测试新增表 → CREATE TABLE
  - 测试删除表 → DROP TABLE
  - 测试破坏性变更注释标记

- [ ] `backend/tests/test_api_diff.py`：
  - 版本创建 → 列表 → 获得版本 ID
  - 创建两个版本 → 对比 → 获得 diff
  - 查看 diff 详情
  - AI 摘要端点（mock AI client）
  - Migration 导出端点
  - 404 错误处理
  - 删除项目后关联删除

**涉及文件**：
- `backend/tests/fixtures/sample_ecommerce_v2.sql`（新建）
- `backend/tests/test_diff_engine.py`（新建）
- `backend/tests/test_diff_migration.py`（新建）
- `backend/tests/test_api_diff.py`（新建）

**验收**：
- [ ] `pytest` 全量通过（含已有 359 个测试 + 新增测试）
- [ ] 新增测试 > 30 个用例
- [ ] 差异检测覆盖率（分支）> 90%

---

## 执行顺序

```
Task 1 ──→ Task 2 ──→ Task 3
                  │        │
                  └── Task 4
                        │
                        └── Task 5
```

每完成一个 Task 暂停，等待 Review 后再继续下一个。
