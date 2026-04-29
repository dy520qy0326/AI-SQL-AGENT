---
name: 09-query-relation-detection
title: 从 SQL 查询语句中识别表关系并可选持久化
status: ARCHIVED
created: 2026-04-29
---

## 摘要

通过解析用户导入的 SQL 查询语句（SELECT 语句中的 JOIN 子句），自动识别表之间的关联关系（LEFT JOIN、INNER JOIN、RIGHT JOIN 等），并以交互方式允许用户选择是否将发现的关系保存到数据库持久化。

## 动机

当前表关系检测仅基于 DDL（CREATE TABLE 语句）中的显式外键和命名约定推断，存在以下局限：

- **外键缺失**：很多数据库（如数仓、历史遗留系统）不定义外键约束，DDL 中没有关系信息
- **隐式推断不准确**：`_id` 后缀推断和同名字段推断置信度低（0.60-0.85），容易误判
- **无查询视角**：SQL 查询中的 JOIN 条件是真实业务需求的体现，是关系发现的高置信度来源

从查询语句中提取 JOIN 关系可弥补上述断层，提供一种用户可自主确认的、高置信度的关系发现途径。

同时，DDL 中的隐式推断（`_id` 后缀、同名字段）虽有一定作用，但置信度低、误报率高，且无法区分业务语义。本提案一并将其移除，DDL 仅保留显式外键转换，所有非外键关系一律通过用户导入的真实查询语句来发现——用户对每条关系有权确认，确保入库的关系准确可靠。

## 范围

### 包含

**SQL 查询解析引擎（P0）**
- 解析 SELECT 语句的 FROM/JOIN 子句，提取：
  - LEFT / RIGHT / INNER / CROSS / FULL OUTER JOIN
  - ON 条件中的关联字段对
  - 表别名解析（`FROM users u JOIN orders o ON u.id = o.user_id`）
- 支持多表 JOIN、子查询 JOIN
- 将解析结果映射到项目中已存在的表名（含别名到真实表名的解析）

**关系预览与确认（P0）**
- 展示从查询中发现的关系列表（source_table、target_table、join_columns、join_type）
- 用户逐条确认是否保存
- 支持 "全部保存" / "全部忽略" / "逐条选择"

**关系持久化（P0）**
- 将用户确认的关系写入现有 `relations` 表
- 复用现有 Relation 模型（relation_type="QUERY_INFERRED", confidence=1.0，source 记录来源查询）
- 与 DDL 派生关系共用同一查询接口（GET /api/projects/{id}/relations）

**API（P0）**
- `POST /api/projects/{id}/query-relations` — 上传 SQL 查询文本，返回解析出的关系预览，不写入数据库
- `POST /api/projects/{id}/query-relations/save` — 传入用户确认的关系 ID 列表，写入数据库

**DDL 关系检测简化（P0）**
- 移除 `RelationDetector.detect()` 中步骤 2-4 的隐式推断逻辑：
  - `_id` 后缀命名推断（confidence=0.85/0.70）
  - 同名字段同类型推断（confidence=0.60）
  - N:M 中间表识别与标记
- DDL 关系检测仅保留步骤 1：显式外键 → Relation 转换（confidence=1.0）
- 被移除的隐式推断能力由查询解析模块替代，用户通过导入真实 SQL 查询来获得更准确的关联

### 不包含

- 查询语句中的 UNION、CTE、子查询内部嵌套关联的深层推断
- 查询性能分析、执行计划
- 自然语言转 SQL 的功能
- 查询语句版本管理
- 从 DML（INSERT/UPDATE/DELETE）中推断关系
- WHERE 子句中隐式连接的推断

### 依赖

- 已有 Parser 基础架构（`app/parser/base.py`、`app/parser/dialect.py`），可扩展支持 DML 解析
- 已有 `relations` 表结构和 Repository
- sqlglot 库（已引入）— 支持 SELECT 语句解析
- 现有 `app/detector/relation.py` — 需修改简化

## 规范

### 数据流

```
用户上传 SQL 查询文本
  ↓
Query Relation Parser 解析 JOIN 子句
  ├─ 识别 JOIN 类型 (LEFT/INNER/RIGHT/CROSS/FULL)
  ├─ 提取 ON 条件中的字段对
  └─ 解析表别名 → 映射到真实表名
  ↓
返回关系预览列表（不写入）
  ├─ 每条包含：source_table, target_table, join_columns, join_type, confidence
  └─ 每条包含唯一临时 ID
  ↓
用户选择要保存的关系（全部/部分/跳过）
  ↓
POST /api/projects/{id}/query-relations/save → 写入 relations 表
```

### 新增数据模型

无需新建表。复用现有 `relations` 表，新增 relation_type 值：

| 字段 | 值 |
|------|------|
| relation_type | "QUERY_INFERRED"（新增） |
| confidence | 1.0（基于用户确认） |
| source | 记录来源查询，如 `"query: SELECT ... FROM users u LEFT JOIN orders o ON u.id = o.user_id"` |

### API 设计

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | /api/projects/{id}/query-relations | `{ "sql": "SELECT ..." }` | 解析查询，返回关系预览 |
| POST | /api/projects/{id}/query-relations/save | `{ "relations": [...] }` | 保存用户确认的关系 |

#### POST /api/projects/{id}/query-relations

请求：
```json
{
  "sql": "SELECT u.name, o.total\nFROM users u\nLEFT JOIN orders o ON u.id = o.user_id\nINNER JOIN products p ON o.product_id = p.id"
}
```

响应：
```json
{
  "dialect": "mysql",
  "queries_parsed": 1,
  "relations": [
    {
      "temp_id": "r1",
      "source_table": "users",
      "source_columns": ["id"],
      "target_table": "orders",
      "target_columns": ["user_id"],
      "join_type": "LEFT JOIN",
      "confidence": 1.0,
      "already_exists": false
    },
    {
      "temp_id": "r2",
      "source_table": "orders",
      "source_columns": ["product_id"],
      "target_table": "products",
      "target_columns": ["id"],
      "join_type": "INNER JOIN",
      "confidence": 1.0,
      "already_exists": false
    }
  ],
  "unmatched_tables": []
}
```

#### POST /api/projects/{id}/query-relations/save

请求：
```json
{
  "relation_ids": ["r1", "r2"]
}
```

响应：
```json
{
  "saved": 2,
  "skipped": 0,
  "relations": [...]
}
```

### 表别名解析规则

1. 显式别名：`FROM users u` → 别名 `u` 映射到表 `users`
2. 隐式别名：`INNER JOIN orders` → 表名 `orders` 即为真实表名
3. Schema 限定名：`FROM public.users u` → schema `public`, 表 `users`
4. 别名反向匹配：`u.id` → 查找别名 `u` → 解析出列所属的表

### 表名匹配

- 解析出的表名先在当前项目已注册表集合中查找（精确匹配、忽略大小写）
- 若未找到，标记为 `unmatched_tables` 并在响应中返回
- unmatched 的表名依然返回关系预览，但无法写入（因为缺少 table_id）
- 子查询别名：`FROM (SELECT ...) AS sub` 跳过，不作为表关系记录

### JOIN 类型映射

| SQL JOIN 类型 | 业务含义 | 影响 |
|---------------|----------|------|
| LEFT JOIN | 左表为主表 | 方向性：左表 → 右表 |
| RIGHT JOIN | 右表为主表 | 方向性：右表 → 左表 |
| INNER JOIN | 双向关联 | 方向性：双向（存储时统一约定，显示时保留原始方向） |
| CROSS JOIN | 笛卡尔积 | 关联字段为空，置信度设为 0.5 |
| FULL OUTER JOIN | 全关联 | 方向性：双向 |

### 错误处理

| 场景 | 行为 |
|------|------|
| SQL 语法解析失败 | 返回 400 + 具体错误位置 |
| SQL 中无 JOIN 子句 | 返回 200 + 空 relations 列表 + 提示信息 |
| 项目不存在 | 返回 404 |
| 查询中的表均未在当前项目注册 | 返回 200 + unmatched_tables 列表，relations 为空 |
| 所有关系已存在（去重） | 返回 200 + `already_exists: true` 标记 |
| 保存时传入不存在的 temp_id | 返回 400 + 无效 ID 列表 |

### 去重逻辑

- 保存前检查：相同的 (source_table_id, source_columns, target_table_id, target_columns) 是否已存在于 relations 表
- 若已存在，跳过保存，在预览中标记 `already_exists: true`

## 验收标准

- [ ] 单条 SELECT 语句的 JOIN 关系能正确解析
- [ ] 多条 SELECT 语句批量解析，合并关系列表
- [ ] LEFT / RIGHT / INNER / CROSS / FULL JOIN 均能正确提取
- [ ] 表别名（含 schema 限定）正确解析为真实表名
- [ ] 项目未注册的表正确标记为 unmatched
- [ ] ON 条件中的复合连接（A AND B）能提取多对关联字段
- [ ] 已存在关系标记 `already_exists`
- [ ] 用户确认保存后，关系正确写入 relations 表
- [ ] 保存后可通 GET /api/projects/{id}/relations 正常查询
- [ ] 已保存的 QUERY_INFERRED 关系在前端 ER 图中正确展示（虚线标注）
- [ ] 无效 SQL 返回 400 + 明确错误信息
- [ ] 单元测试覆盖率 > 80%

**DDL 检测简化**
- [ ] `RelationDetector.detect()` 只保留显式外键转换，无隐式推断逻辑
- [ ] 移除 `_singularize()` 函数及其相关代码
- [ ] 移除 `_make_inferred()` 辅助函数（如不再被使用）

## 备注

- 使用 sqlglot 解析 SELECT 语句（已引入，当前用于 DDL 解析）
- Query Relation Parser 作为独立模块 `app/query_relation/`，不耦合现有 DDL Parser
- 复用现有 Repository 层写入 relations 表
- 前端可扩展 "导入 SQL 查询" 按钮，调用 query-relations API 后展示预览列表供用户勾选
