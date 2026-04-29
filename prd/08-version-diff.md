# PRD: 版本对比模块 (Version Diff)

## 1. 产品概述

版本对比模块允许用户上传同一项目的 DDL 新版本，自动对比两版之间的 schema 差异，以结构化的方式展示变更点，帮助团队在数据库演进过程中追踪变更。

## 2. 目标用户

- **主要用户**：DBA、后端开发在 Code Review 或数据库迁移时使用
- **典型场景**：
  - "这次迭代增加了哪些表？"
  - "谁把 orders.total_amount 的类型改了？"
  - "需要检查新增字段有没有默认值"

## 3. 功能需求

### P0 — Schema Diff

| 功能 | 说明 |
|------|------|
| 表级差异 | 新增表、删除表、重命名表（启发式匹配） |
| 字段级差异 | 新增字段、删除字段、字段类型/长度/默认值/NULL 属性变更 |
| 索引差异 | 新增索引、删除索引 |
| 关系差异 | 新增外键、删除外键 |

### P1 — 变更展示

| 功能 | 说明 |
|------|------|
| 变更统计面板 | 总计：+N 表，-M 表，+K 字段，-L 字段，+X 索引 |
| 分层展示 | 按变更类型分 tab：表变更 / 字段变更 / 索引变更 |
| 内联高亮 | 对变更字段进行 before → after 对比展示 |
| 破坏性变更标记 | 标记可能导致兼容性问题的变更（如字段类型缩窄、删除字段） |

### P2 — 增强功能

| 功能 | 说明 |
|------|------|
| AI 变更摘要 | AI 生成变更描述："新增了 payment_logs 表用于记录支付回调" |
| SQL Migration 导出 | 自动生成 ALTER TABLE 迁移脚本 |
| 变更影响分析 | 变更的表关联了哪些下游表，影响哪些模块 |

## 4. 差异检测规则

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

## 5. AI 变更摘要 Prompt

```
分析以下两个版本数据库 schema 之间的差异：

旧版表数: {old_count}
新版表数: {new_count}

变更详情：
{structured_diff_json}

请生成一份简洁的变更摘要（3-5 句话），包括：
1. 整体变更范围（小/中/大）
2. 最重要的 3 个变更
3. 是否存在破坏性变更
```

## 6. 数据模型

```yaml
ProjectVersion:
  id: UUID
  project_id: UUID (FK → Project)
  version_tag: string         # "v1.0", "v2.0" 或自动 "YYYYMMDD-N"
  file_hash: string           # SQL 文件 SHA256
  created_at: datetime

SchemaDiff:
  id: UUID
  project_id: UUID
  old_version_id: UUID
  new_version_id: UUID
  diff_data: JSON             # 完整差异结构
  summary: string?            # AI 生成的摘要
  breaking_changes: boolean
  created_at: datetime

# diff_data 结构
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

## 7. 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/versions | 创建新版本（上传 SQL） |
| GET | /api/projects/{id}/versions | 版本列表 |
| POST | /api/projects/{id}/diff | 指定两个版本进行对比 |
| GET | /api/projects/{id}/diff/{diff_id} | 获取对比结果 |
| POST | /api/projects/{id}/diff/{diff_id}/ai-summary | AI 生成变更摘要 |
| POST | /api/projects/{id}/diff/{diff_id}/migration | 导出 ALTER 脚本 |

## 8. 验收标准

- [ ] 新增一张表 + 删除一张表，差异列表正确
- [ ] 字段类型从 int → bigint，正确标记为"类型变更"
- [ ] 字段改名不误报为"删除+新增"（利用字段顺序+类型匹配）
- [ ] 变更统计数字和实际变更一致
- [ ] 破坏性变更（NOT NULL → NULL 逆操作、类型缩窄）正确标记
- [ ] AI 摘要没有幻觉（不提及不存在的变更）
- [ ] 生成的 ALTER TABLE 脚本语法正确
