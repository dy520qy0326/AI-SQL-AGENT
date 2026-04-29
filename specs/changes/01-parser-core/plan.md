# Plan: 01-parser-core — SQL DDL Parser 核心引擎

---
status: REVIEWED
---

## 架构影响

Parser 是整个系统的**底层基础模块**，位于以下调用链的最前端：

```
用户上传 .sql → Parser → Store (持久化) → Relation Detector / AI Service / Visualization
```

- **新增目录**：`backend/app/parser/`
- **无外部依赖变更**：不引入新服务、不修改现有模块
- **接口契约**：Parser 输出结构化元数据，下游 Store 模块直接消费

## 技术选型

| 决策 | 选择 | 理由 |
|------|------|------|
| SQL 解析库 | sqlglot | 支持 MySQL / PostgreSQL 多方言，容错性强，Python 生态活跃 |
| 输出模型 | Pydantic BaseModel | 类型安全、可直接序列化为 JSON、与 FastAPI 天然集成 |
| 测试框架 | pytest | 项目默认，参数化测试适合 DDL 样本验证 |
| 方言检测 | sqlglot 内置方言检测 + 规则兜底 | 减少手动指定负担 |

## 组件设计

### 类结构

```
parser/
  __init__.py
  base.py          → BaseParser (抽象基类)
  mysql.py         → MySQLParser (MySQL 方言实现)
  postgres.py      → PostgreSQLParser (PostgreSQL 方言实现)
  dialect.py       → 方言检测工具函数
  models.py        → Pydantic 输出模型定义
```

#### BaseParser（抽象基类）

```
BaseParser
├── parse(sql_text: str) -> ParseResult        # 入口方法
├── _parse_statements(sql_text) -> list         # 语句分割
├── _parse_create_table(statement) -> Table     # 单表解析
├── _extract_columns(statement) -> list[Column] # 字段提取
├── _extract_indexes(statement) -> list[Index]  # 索引提取
├── _extract_foreign_keys(statement) -> list    # 外键提取
├── _detect_dialect(sql_text) -> str            # 方言检测
└── dialect: str                                # 方言标识
```

- `_extract_*` 方法在子类中重载以处理方言差异
- `parse()` 为模板方法，定义流程骨架

#### MySQLParser / PostgreSQLParser

继承 BaseParser，重写方言特定的提取逻辑：
- 引号规则不同（`` ` `` vs `"`）
- 数据类型命名差异（`TINYINT` vs `SMALLINT`）
- AUTO_INCREMENT 语法差异
- 注释语法差异（`-- ` vs `--`）

#### 输出模型 (models.py)

```python
class Column(BaseModel):
    name: str
    type: str
    length: int | None = None
    nullable: bool = True
    default: str | None = None
    primary_key: bool = False
    comment: str = ""

class Index(BaseModel):
    name: str
    unique: bool = False
    columns: list[str]

class ForeignKey(BaseModel):
    columns: list[str]
    ref_table: str
    ref_columns: list[str]

class Table(BaseModel):
    name: str
    schema: str = ""
    comment: str = ""
    columns: list[Column] = []
    indexes: list[Index] = []
    foreign_keys: list[ForeignKey] = []

class ParseError(BaseModel):
    statement_index: int
    line: int
    message: str

class ParseResult(BaseModel):
    dialect: str
    tables: list[Table] = []
    errors: list[ParseError] = []
```

### 方言检测策略

1. 如果用户显式指定方言 → 直接使用
2. 否则按以下规则自动检测：
   - 含 `AUTO_INCREMENT` → MySQL
   - 含 `SERIAL` 或 `::` 类型转换 → PostgreSQL
   - 含 `` ` `` 反引号引用的标识符 → MySQL
   - 默认回退到 MySQL（更常见）

## 实现路径

按任务单元分步实现：

| 步骤 | 内容 | 交付 |
|------|------|------|
| 1 | 项目骨架和基础设施 | `main.py`、`config.py`、`requirements.txt`、Pydantic 模型 |
| 2 | BaseParser + 语句分割 + 方言检测 | 可运行的基本解析流程 |
| 3 | CREATE TABLE + 字段解析 + 主键 | 支持单表基础解析 |
| 4 | 外键解析（列级 + 表级） | 外键完整覆盖 |
| 5 | 索引解析 | INDEX / UNIQUE / KEY |
| 6 | MySQL 方言适配 | 引号、专用类型、AUTO_INCREMENT |
| 7 | PostgreSQL 方言适配 | 引号、SERIAL、类型转换 |
| 8 | 错误处理 + 容错 | 错误跳过 + 记录 |
| 9 | MySQL DDL 样本测试 | employees.sql 等标准样本验证 |
| 10 | PostgreSQL DDL 样本测试 | 对应样本验证 |
| 11 | 边界测试 | 空文件、含语法错误的文件、大文件 |

## 风险分析

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| sqlglot 某方言解析不完整 | 中 | 中 | 针对不支持的语法用正则补充；贡献补丁或 fork 修复 |
| DDL 中存在 sqlglot 未覆盖的语法特性 | 低 | 低 | 容错跳过，记录到 errors |
| 方言自动检测误判 | 低 | 低 | 用户可显式指定方言覆盖检测结果 |
| 超大文件（5000+ 行） | 低 | 低 | sqlglot 解析性能可接受，必要时后续加流式解析 |

## 工作量估算

约 400-600 行 Python 代码（含模型定义），含测试约 800-1000 行。
