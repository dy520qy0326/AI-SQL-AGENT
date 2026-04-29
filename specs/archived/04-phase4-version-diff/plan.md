---
name: 04-phase4-version-diff
title: Phase 4 — 技术实施方案
status: REVIEWED
created: 2026-04-29
---

## 架构影响分析

### 新增模块

```
backend/app/
├── diff/
│   ├── __init__.py
│   ├── engine.py          # Schema diff 核心引擎
│   └── migration.py       # ALTER TABLE 脚本生成
├── schemas/
│   ├── version.py         # Version/Diff 请求响应 Schema
├── api/
│   └── diff.py            # 版本和差异 API 路由
```

### 修改模块

| 文件 | 变更 |
|------|------|
| `app/db/models.py` | 新增 ProjectVersion、SchemaDiff 两个 ORM 模型 |
| `app/store/repository.py` | 新增 version CRUD、diff CRUD、已存版本列表方法 |
| `app/schemas/__init__.py` | 暴露 version/diff schemas |
| `app/main.py` | 注册 diff_router |

### 不涉及的部分

- `app/parser/` — 直接使用现有 ParseResult，不改动
- `app/detector/` — 不变
- `app/ai/` — 重用 AI client 做摘要，不修改现有代码
- `app/nl/` — 不变
- `app/viz/` — 不变
- `app/docgen/` — 不变

### 数据流

```
上传新版 SQL → 解析 (现有 Parser) → 保存版本快照 (ProjectVersion)
                                        ↓
指定 old_version + new_version → diff engine → SchemaDiff
                                        ↓
                              ├─ 调用 AI 生成摘要
                              └─ 生成 ALTER TABLE 迁移脚本
```

## 实现路径

### Task 1: 数据模型 + Repository 扩展

**目标**：新增 ProjectVersion 和 SchemaDiff ORM 模型及 CRUD。

- `app/db/models.py` 新增：
  - `ProjectVersion`：
    - id: String(36) PK, default uuid
    - project_id: FK → projects.id, ondelete CASCADE
    - version_tag: String(100)
    - file_hash: String(64)
    - parse_result: JSON（解析结果的完整快照）
    - created_at: DateTime, default utcnow
  - `SchemaDiff`：
    - id: String(36) PK, default uuid
    - project_id: FK → projects.id, ondelete CASCADE
    - old_version_id: FK → project_versions.id
    - new_version_id: FK → project_versions.id
    - diff_data: JSON
    - summary: Text, nullable
    - breaking_changes: Boolean, default False
    - created_at: DateTime, default utcnow

- `app/store/repository.py` 新增：
  - Version
    - `create_version(project_id, version_tag, file_hash, parse_result)` → ProjectVersion
    - `list_versions(project_id)` → List[ProjectVersion]
    - `get_version(version_id)` → ProjectVersion | None
    - `delete_version(version_id)` → bool
  - Diff
    - `create_diff(project_id, old_version_id, new_version_id, diff_data, summary=None, breaking_changes=False)` → SchemaDiff
    - `get_diff(diff_id)` → SchemaDiff | None
    - `list_diffs(project_id)` → List[SchemaDiff]
    - `update_diff_summary(diff_id, summary)` → None

**涉及文件**：
- `backend/app/db/models.py`（修改）
- `backend/app/store/repository.py`（修改）
- `backend/app/schemas/version.py`（新建）

---

### Task 2: Diff Engine — 核心差异检测

**目标**：实现两版 parse_result 之间的结构化差异检测。

- 创建 `app/diff/engine.py`：
  - `compute_diff(old_result: dict, new_result: dict)` → dict
  - 表级对比：
    - 表名精确匹配 → 同一表
    - 未匹配的表做重名检测：编辑距离 + 字段重叠度（字段集 Jaccard 相似度 > 0.8）
    - 输出：tables_added、tables_removed、tables_renamed
  - 字段级对比（同一表内）：
    - 字段名精确匹配 → 属性对比（类型/长度/NULL/默认值）
    - 字段名不匹配 → 新增/删除判断
    - 字段改名检测：同一位序附近 + 类型一致
    - 输出：fields_added、fields_removed、fields_modified（含 before/after）
  - 索引对比：
    - 索引名精确匹配 → 忽略（视为相同）
    - 不匹配 → 新增/删除
    - 输出：indexes_added、indexes_removed
  - 关系对比：
    - source + target + columns 组合匹配
    - 输出：relations_added、relations_removed
  - 破坏性变更判定：
    - 类型缩窄 → breaking
    - NOT NULL → NULL → breaking
    - 删除字段/表/索引/关系 → breaking
    - 输出：breaking_changes: bool, breaking_details: list
  - 变更统计：tables_changed、fields_changed、indexes_changed、relations_changed 各分类计数

**数据传入**：两个版本的 parse_result JSON（由 Repository 从 ProjectVersion.parse_result 读取）

**parse_result 的结构**：
```json
{
  "dialect": "mysql",
  "tables": [
    {
      "name": "orders",
      "schema_name": null,
      "comment": null,
      "columns": [
        {"name": "id", "data_type": "INT", "length": null, "nullable": false, "default_value": null, "is_primary_key": true, "comment": null},
        ...
      ],
      "indexes": [
        {"name": "idx_user", "unique": false, "columns": ["user_id"]}
      ],
      "foreign_keys": [
        {"columns": ["user_id"], "ref_table_name": "users", "ref_columns": ["id"], "constraint_name": "fk_orders_user"}
      ]
    }
  ]
}
```

---

### Task 3: Migration 脚本生成 + AI 摘要

**目标**：根据 diff 数据生成 ALTER TABLE 脚本，以及 AI 变更摘要。

- 创建 `app/diff/migration.py`：
  - `generate_alter_scripts(diff_data: dict, dialect: str)` → str
  - 逐表生成 ALTER TABLE 语句：
    - 新增表：`CREATE TABLE ...`（从新版本的 table 定义复制）
    - 删除表：`DROP TABLE IF EXISTS ...`
    - 新增字段：`ALTER TABLE t ADD COLUMN ...`
    - 删除字段：`ALTER TABLE t DROP COLUMN ...`
    - 修改字段：`ALTER TABLE t MODIFY COLUMN ...`（MySQL）/ `ALTER TABLE t ALTER COLUMN ...`（PostgreSQL）
    - 新增索引：`CREATE INDEX ...`
    - 删除索引：`DROP INDEX ...`
  - 按表组织，拼接为完整 SQL 脚本

- AI 摘要（重用 `app/ai/client.py`）：
  - 在 `app/diff/engine.py` 或 API 层调用 AI
  - Prompt：传入结构化 diff_data，AI 返回 3-5 句变更摘要
  - 标记是否包含破坏性变更

---

### Task 4: API 路由 + 集成

**目标**：创建版本和差异的 API 端点，注册到应用。

- 创建 `app/api/diff.py`：
  - `POST /api/projects/{project_id}/versions` — 创建版本：接收 SQL 内容，调用 Parser 解析，保存 ProjectVersion
  - `GET /api/projects/{project_id}/versions` — 版本列表
  - `POST /api/projects/{project_id}/diff` — 对比：body `{old_version_id, new_version_id}`，调用 engine.compute_diff，保存 SchemaDiff
  - `GET /api/projects/{project_id}/diff/{diff_id}` — 获取对比结果
  - `POST /api/projects/{project_id}/diff/{diff_id}/ai-summary` — AI 生成变更摘要
  - `POST /api/projects/{project_id}/diff/{diff_id}/migration` — 导出 ALTER 脚本

- 创建 `app/schemas/version.py`：
  - `VersionCreateRequest(sql_content, version_tag?)`
  - `VersionResponse(id, project_id, version_tag, file_hash, tables_count, created_at)`
  - `DiffRequest(old_version_id, new_version_id)`
  - `DiffResponse(id, project_id, diff_data, summary, breaking_changes, created_at)`
  - `DiffListResponse(items, total)`

- `app/main.py` 注册 diff_router

- `app/store/repository.py` 新增：
  - 创建 version 时保存 parse_result 快照的方法
  - 上传 SQL 可直接复用现有流程（解析 + 覆盖项目表），同时保存为新 version

---

### Task 5: 测试

**目标**：单元测试 + 集成测试覆盖 diff 全链路。

- `backend/tests/test_diff_engine.py`：
  - 测试表级差异（新增/删除/重命名）
  - 测试字段级差异（新增/删除/类型变更/NULL 变更/默认值变更）
  - 测试字段重命名检测
  - 测试索引差异
  - 测试关系差异
  - 测试破坏性变更判定
  - 测试边界情况：完全相同 → 空 diff
  - 测试边界情况：空表 → 全新增
- `backend/tests/test_diff_migration.py`：
  - MySQL 和 PostgreSQL 的 ALTER 脚本生成
  - 测试新增表 → CREATE TABLE
  - 测试修改字段 → ALTER TABLE MODIFY
- `backend/tests/test_api_diff.py`：
  - 版本创建 → 列表 → 对比 → 查询结果全链路
  - AI 摘要端点
  - 迁移脚本导出端点
  - 404/400 错误处理

**测试 fixture**：
- 复用 `sample_ecommerce.sql` 作为 version 1
- 创建 `sample_ecommerce_v2.sql` 作为 version 2（包含表/字段/索引变更）

## 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 字段重命名误报为删除+新增 | diff 结果不准确 | 编辑距离 + 同位置匹配 + 类型一致三重校验 |
| parse_result 快照格式变更 | 旧版本快照无法对比 | 定义稳定 JSON schema，解析器升级时做向后兼容 |
| 大项目 diff 计算慢 | API 响应慢 | 差异检测为纯内存计算，O(n*m) 复杂度可接受 |
| AI 摘要幻觉 | 描述不存在的变更 | Prompt 约束严格引用 diff_data；在前端标记"AI 生成" |

## 工作量估算

| Task | 估算 |
|------|------|
| Task 1: 数据模型 + Repository | 小 |
| Task 2: Diff Engine | 大 |
| Task 3: Migration + AI 摘要 | 中 |
| Task 4: API 路由 + 集成 | 中 |
| Task 5: 测试 | 中 |
