---
name: 09-query-relation-detection
title: 从 SQL 查询语句中识别表关系并可选持久化
status: REVIEWED
created: 2026-04-29
---

## 技术方案

### 架构概述

```
┌─ app/query_relation/parser.py     ← sqlglot 解析 SELECT 语句的 JOIN
│   parse_join_relations(sql, tables_dict) → [DiscoveredRelation]
│
├─ app/api/query_relations.py       ← 两个新 API 端点
│   POST /api/projects/{id}/query-relations        → 解析预览
│   POST /api/projects/{id}/query-relations/save   → 确认保存
│
├─ app/schemas/query_relation.py    ← 请求/响应 Pydantic 模型
│
├─ app/detector/relation.py         ← 简化：仅保留显式外键
│   (移除 _id 推断、同名字段推断、N:M 检测)
│
└─ app/main.py                      ← 注册新 router
```

### 1. Query Relation Parser（新建模块）

**路径**: `app/query_relation/parser.py`

使用 sqlglot 解析 SELECT 语句，提取所有 JOIN 子句中的表关系和关联字段。

```python
@dataclass
class DiscoveredRelation:
    temp_id: str
    source_table: str       # 真实表名（已解析别名）
    source_columns: list[str]
    target_table: str
    target_columns: list[str]
    join_type: str          # "LEFT JOIN" / "INNER JOIN" / etc.
    confidence: float

def parse_join_relations(
    sql: str,
    tables_dict: dict[str, Table],  # {lowercase_name: Table}
    dialect: str = "mysql",
) -> tuple[list[DiscoveredRelation], list[str]]:
    """Parse SQL SELECT statement(s), return discovered relations + unmatched table names."""
```

**关键实现细节**:
- 使用 `sqlglot.transpile()` 分割多条 SQL 语句
- 对每条 SELECT 语句遍历 AST 的 JOIN 节点
- 解析表别名映射：`FROM users u` → `{u: users}`
- 解析 ON 条件的二元表达式树，提取 `left = right` 形式的字段对
- 字段引用如 `u.id` 通过别名映射到真实表名
- 复合条件 `A AND B` 递归提取多对关联字段
- 支持 JOIN 类型的识别：LEFT/RIGHT/INNER/CROSS/FULL OUTER
- 表名匹配：优先精确匹配（忽略大小写），未匹配的加入 unmatched_tables

**边界情况处理**:
- 子查询别名（`FROM (SELECT ...) AS sub`）— 跳过
- SELF JOIN — 同一表不同别名，视为自引用关系
- 无别名的表引用 — 直接用表名
- Schema 限定名（`public.users`）— 提取表名部分匹配

### 2. API 端点

**路径**: `app/api/query_relations.py`

#### `POST /api/projects/{id}/query-relations`

流程：
1. 验证项目存在
2. 获取项目表字典（`Repository.get_project_tables_dict`）
3. 调用 `parse_join_relations(sql, tables_dict, project.dialect)`
4. 对每条 DiscoveredRelation，检查是否已存在于 relations 表
5. 构建响应（含 already_exists 标记）

#### `POST /api/projects/{id}/query-relations/save`

流程：
1. 验证项目存在
2. 重新解析 SQL（保持幂等性）
3. 过滤出用户选择的 temp_id
4. 批量写入 relations 表（relation_type="QUERY_INFERRED", confidence=1.0）
5. 已存在的跳过（去重）

### 3. Schema 定义

**路径**: `app/schemas/query_relation.py`

```python
class QueryRelationRequest(BaseModel):
    sql: str

class QueryRelationPreview(BaseModel):
    temp_id: str
    source_table: str
    source_columns: list[str]
    target_table: str
    target_columns: list[str]
    join_type: str
    confidence: float
    already_exists: bool = False

class QueryRelationResponse(BaseModel):
    dialect: str
    queries_parsed: int
    relations: list[QueryRelationPreview]
    unmatched_tables: list[str]

class SaveRelationRequest(BaseModel):
    relation_ids: list[str]

class SaveRelationResponse(BaseModel):
    saved: int
    skipped: int
    relations: list[dict]  # 已保存的关系详情
```

### 4. DDL 关系检测简化

**文件**: `app/detector/relation.py`

当前步骤 | 操作
---------|------
Step 1: 显式外键 → Relation | ✅ 保留
Step 2: `_id` 后缀推断 | ❌ 移除
Step 3: 同名字段同类型推断 | ❌ 移除
Step 4: N:M 中间表识别 | ❌ 移除
Step 5: 去重 | ✅ 保留（覆盖显式外键自身可能的重复）

移除内容：
- `_singularize()` 函数及其测试类 `TestSingularize`
- `_make_inferred()` 辅助函数
- Step 2-4 的循环和逻辑块
- `covered_pairs` 集合（不再需要，因为步骤 1 不会产生冲突）

简化后的 `detect()` 方法：
1. 查询项目表和外键
2. 外键 → Relation 转换（confidence=1.0）
3. 运行去重
4. 返回结果

### 5. Repository 层

在 `Repository` 中新增：

```python
async def relation_exists(
    self, project_id: str, source_table_id: str, target_table_id: str,
    source_columns: list[str], target_columns: list[str],
) -> bool:
    """Check if an identical relation already exists."""

async def save_query_relations(
    self, project_id: str, relations: list[RelationData]
) -> list[Relation]:
    """Append relations without deleting existing ones (unlike save_relations which replaces all)."""
```

**注意**: 现有的 `save_relations()` 是全量替换（先删后插），用于 DDL 上传后的关系重建。Query relation 的保存是增量追加，二者分开。

### 6. 测试计划

**新增** `backend/tests/test_query_relation_parser.py`:
- 单表 JOIN 解析
- 多表 JOIN + 复合 ON 条件
- 别名解析
- 子查询跳过
- SELF JOIN
- Schema 限定名
- CROSS JOIN（无 ON 条件）
- 多条 SQL 语句
- 未匹配表标记
- 无效 SQL 错误

**修改** `backend/tests/test_detector.py`:
- 删除 `test_id_suffix_exact_match`、`test_id_suffix_plural_match`、`test_same_name_same_type_inference`、`test_nm_bridge_table_marking`
- 删除 `TestSingularize` 类
- 修改 `test_dedup_keeps_highest_confidence`：现在只有外键，无需去重测试多种置信度
- 保留 `test_explicit_fk_detection`、`test_self_referencing_fk`、`test_no_relation_for_missing_target`

**新增** `backend/tests/test_api_query_relations.py`:
- API 端点集成测试
- 预览 → 保存 完整流程

### 7. 注册路由

在 `app/main.py` 中添加：
```python
from app.api.query_relations import router as query_relations_router
app.include_router(query_relations_router)
```

### 风险点

| 风险 | 缓解措施 |
|------|----------|
| sqlglot 对不同 SQL 方言的兼容性 | 复用项目配置的 dialect，提取时使用 sqlglot 的 dialect 参数 |
| 复杂 ON 条件（非等值连接、函数调用） | 只提取 `column = column` 形式的等值条件，其他跳过并记录 |
| 子查询嵌套层级过深 | 限制 AST 递归深度（默认 10 层） |
| 大量 SQL 批量解析性能 | sqlglot 单条解析 < 1ms，千条语句可接受；不做额外限制 |

### 工作量估算

| 模块 | 文件 | 预估代码行 |
|------|------|-----------|
| Query Parser | `app/query_relation/` | ~150 行 |
| API | `app/api/query_relations.py` | ~80 行 |
| Schemas | `app/schemas/query_relation.py` | ~50 行 |
| Repository 扩展 | `app/store/repository.py` | ~30 行 |
| Detector 简化 | `app/detector/relation.py` | -60 行 |
| Main 注册 | `app/main.py` | +2 行 |
| 测试 | `tests/` | ~200 行 |
| **总计** | | **~450 行** |
