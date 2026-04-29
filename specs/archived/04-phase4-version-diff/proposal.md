---
name: 04-phase4-version-diff
title: Phase 4 — 版本对比 (Version Diff)
status: ARCHIVED
created: 2026-04-29
---

## 摘要

在 Phase 1-3 的基础上，增加版本管理能力：用户上传同一项目的新版 DDL 后，系统自动对比新旧版本的 schema 差异，以结构化方式展示变更点，帮助团队在数据库演进过程中追踪变更。

## 动机

当前系统只能解析单次上传的 SQL，无法追踪数据库 schema 的演进历史。在实际开发中，数据库结构会随迭代不断变化，团队需要一种方式了解变更历史：

- "这次迭代增加了哪些表？"
- "是谁把 orders.total_amount 的类型改了？"
- "新增的字段有没有默认值？"
- "这个变更是否兼容现有业务？"

Phase 4 填补这一缺口，使系统从"单次快照"升级为"版本可追溯"。

## 范围

### 包含

**P0 — Schema Diff**
- 表级差异：新增表、删除表、重命名表（启发式匹配）
- 字段级差异（核心）：新增字段、删除字段、字段类型/长度/默认值/NULL 属性变更
- 索引差异：新增索引、删除索引
- 关系差异：新增外键、删除外键
- 变更统计面板：总计 +/- 表、字段、索引、关系

**P1 — 变更展示**
- 分层展示：按变更类型分组（表/字段/索引/关系）
- 内联对比：对变更字段展示 before → after 对比
- 破坏性变更标记：标记类型缩窄、NOT NULL 移除等不兼容变更

**P2 — 增强（本次实现包含）**
- AI 变更摘要：AI 生成变更描述
- SQL Migration 导出：自动生成 ALTER TABLE 迁移脚本

### 不包含

- 变更影响分析（变更的表关联哪些下游表）— 后续提案
- Branch/MR 集成 — 后续提案
- 版本回滚 — 后续提案
- 多版本可视化时间线 — P3

### 依赖

- PRD: `prd/08-version-diff.md`
- 内部依赖：Phase 1-3 的解析引擎 + 元数据存储 + AI Service

## 数据模型

### ProjectVersion
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| project_id | FK → Project | 所属项目 |
| version_tag | str | "v1.0" 或自动 "YYYYMMDD-N" |
| file_hash | str | SQL 文件 SHA256 |
| parse_result | JSON | 解析结果的快照 |
| created_at | datetime | |

### SchemaDiff
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| project_id | FK → Project | |
| old_version_id | FK → ProjectVersion | |
| new_version_id | FK → ProjectVersion | |
| diff_data | JSON | 完整差异结构 |
| summary | str? | AI 生成的摘要 |
| breaking_changes | bool | 是否存在破坏性变更 |
| created_at | datetime | |

### diff_data 结构
```json
{
  "tables_added": [...],
  "tables_removed": [...],
  "tables_renamed": [...],
  "fields_added": [{"table": "...", "field": "...", "definition": {...}}],
  "fields_removed": [...],
  "fields_modified": [{"table": "...", "field": "...", "before": {...}, "after": {...}}],
  "indexes_added": [...],
  "indexes_removed": [...],
  "relations_added": [...],
  "relations_removed": [...]
}
```

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/versions | 创建新版本（上传 SQL） |
| GET | /api/projects/{id}/versions | 版本列表 |
| POST | /api/projects/{id}/diff | 指定两个版本进行对比 |
| GET | /api/projects/{id}/diff/{diff_id} | 获取对比结果 |
| POST | /api/projects/{id}/diff/{diff_id}/ai-summary | AI 生成变更摘要 |
| POST | /api/projects/{id}/diff/{diff_id}/migration | 导出 ALTER 脚本 |

## 差异检测规则

| 变更类型 | 检测方法 | 示例 |
|---------|---------|------|
| 新增表 | 旧版没有的表 | +payment_logs |
| 删除表 | 新版没有的表 | -old_orders |
| 重命名表 | 编辑距离 + 字段重叠度 > 80% | users → users_v2 |
| 新增字段 | 表存在，字段仅在新版 | +orders.coupon_id |
| 删除字段 | 表存在，字段仅在旧版 | -orders.discount_old |
| 类型变更 | 字段名相同，类型不同 | int → bigint |
| NULL 变更 | nullable 属性变化 | NULL → NOT NULL |
| 默认值变更 | default 值变化 | 0 → null |
| 新增索引 | 仅新版有 | +idx_coupon |
| 删除索引 | 仅旧版有 | -idx_old_discount |

## 破坏性变更判定

以下情况标记为 breaking_change：
- 字段类型缩窄（bigint → int, varchar(255) → varchar(100)）
- NOT NULL → NULL（上层代码可能不再传值）
- 删除字段
- 删除表
- 删除外键

## 验收标准

- [ ] 新增一张表 + 删除一张表，差异列表正确
- [ ] 字段类型从 int → bigint，正确标记为"类型变更"
- [ ] 字段改名不误报为"删除+新增"（利用字段顺序+类型匹配）
- [ ] 变更统计数字和实际变更一致
- [ ] 破坏性变更正确标记
- [ ] AI 摘要不提及不存在的变更
- [ ] 生成的 ALTER TABLE 脚本语法正确
- [ ] 版本 CRUD 完整（创建→列表→对比→删除）
- [ ] 单元测试覆盖率 > 85%

## 备注

- 字段重命名检测使用"编辑距离 + 类型匹配 + 顺序相近"组合启发式，降低误报率
- 迁移脚本生成基于字段级操作拼接，不做语义分析
- AI 摘要为 P2 功能，不影响核心 diff 功能
