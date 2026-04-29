# PRD: 元数据存储模块 (Metadata Store)

## 1. 产品概述

Metadata Store 负责将 SQL Parser 输出的结构化元数据进行持久化存储、查询和管理。它是所有上游模块（关系检测、可视化、AI 服务）的数据中枢。

## 2. 目标用户

- **下游消费者**：Relation Detector、Visualization API、AI Service、前端各页面
- **间接用户**：通过 REST API 查询表结构的开发者

## 3. 功能需求

### P0 — 基础 CRUD

| 功能 | 说明 |
|------|------|
| 项目创建 | 上传 SQL 前创建项目容器 |
| 元数据写入 | 解析完成后批量写入表/字段/索引/外键 |
| 元数据查询 | 按项目查询表列表、字段详情、关系列表 |
| 项目删除 | 删除项目及其全部元数据 |

### P1 — 管理功能

| 功能 | 说明 |
|------|------|
| 项目列表 | 分页、搜索、排序（按创建时间/表数量） |
| 元数据更新 | 重新上传覆盖，保留历史版本（见 Version Diff） |
| 批量导出 | 导出项目元数据为 JSON |

### P2 — 高级功能

| 功能 | 说明 |
|------|------|
| 表搜索 | 跨项目搜索表名/字段名 |
| 血缘追踪 | 查询指定字段被哪些外键引用 |
| 统计看板 | 项目维度：表数量、关系数量、缺失注释比例 |

## 4. 数据模型

```yaml
Project:
  id: UUID (PK)
  name: string              # 项目名称
  description: string?      # 描述
  dialect: string           # 方言: mysql / postgresql / sqlite
  created_at: datetime
  updated_at: datetime

Table:
  id: UUID (PK)
  project_id: UUID (FK → Project)
  schema_name: string       # 默认 public
  name: string              # 表名
  comment: string?          # 表注释
  engine: string?           # MySQL: InnoDB/MyISAM...
  table_collation: string?  # 字符集
  created_at: datetime

Column:
  id: UUID (PK)
  table_id: UUID (FK → Table)
  name: string
  ordinal_position: int     # 字段顺序
  data_type: string         # int / varchar / decimal...
  length: int?
  precision: int?
  scale: int?
  nullable: boolean
  default_value: string?
  is_primary_key: boolean
  auto_increment: boolean
  comment: string?
  enum_values: JSON?        # ENUM 类型时存储允许值列表

Index:
  id: UUID (PK)
  table_id: UUID (FK → Table)
  name: string
  unique: boolean
  columns: JSON             # ["col1", "col2"]

ForeignKey:
  id: UUID (PK)
  table_id: UUID (FK → Table)           # 来源表
  columns: JSON                          # 来源列 ["dept_id"]
  ref_table_id: UUID (FK → Table)       # 目标表
  ref_columns: JSON                      # 目标列 ["id"]
  constraint_name: string?
  delete_rule: string?                   # CASCADE / SET NULL...

Relation:                   # 显式外键 + 推断关系统一存储
  id: UUID (PK)
  project_id: UUID (FK → Project)
  source_table_id: UUID
  source_columns: JSON
  target_table_id: UUID
  target_columns: JSON
  relation_type: enum       # FOREIGN_KEY / INFERRED / AI_SUGGESTED
  confidence: float         # 置信度 0.0~1.0
  source: string?           # 来源说明，如 "user_id matches user.id"
```

## 5. API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects | 创建项目 |
| GET | /api/projects | 项目列表 |
| GET | /api/projects/{id} | 项目详情 + 统计 |
| DELETE | /api/projects/{id} | 删除项目 |
| POST | /api/projects/{id}/upload | 上传 SQL 并解析 |
| GET | /api/projects/{id}/tables | 表列表 |
| GET | /api/projects/{id}/tables/{tid} | 表详情+字段+索引 |
| GET | /api/projects/{id}/relations | 关系列表 |
| GET | /api/projects/{id}/graph | 图数据(nodes+edges) |
| GET | /api/projects/{id}/stats | 元数据统计 |

## 6. 事务与一致性

| 场景 | 策略 |
|------|------|
| SQL 解析 + 写入 | 单次上传在一个事务内完成，解析失败全部回滚 |
| 并发上传 | 同一项目上传加写锁，防止脏写 |
| 重名表处理 | 同一项目中表名 + schema 唯一约束 |
| 软删除 | 项目标记 deleted_at，保留 30 天后物理清除 |

## 7. 验收标准

- [ ] 创建/查询/删除项目完整 CRUD 可用
- [ ] 上传 DDL → 解析 → 持久化，数据完整无丢失
- [ ] 10000 条 Column 记录查询 < 200ms（索引覆盖）
- [ ] 项目级联删除正确（删除项目 → 删除所有关联表/字段/关系）
- [ ] 解析失败时无脏数据残留
- [ ] 数据库迁移脚本可回滚
