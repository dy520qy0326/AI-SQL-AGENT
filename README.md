# AI SQL Agent

> 上传 SQL DDL 文件，自动解析数据库表结构并识别表间关联关系，借助 AI 能力提供可视化、智能问答和文档生成。

## 功能概览

| 功能 | 说明 | 状态 |
|------|------|------|
| SQL 解析 | 解析 `CREATE TABLE` DDL，提取表、字段、类型、约束、外键 | ✅ Phase 1 |
| 方言支持 | MySQL、PostgreSQL 自动方言检测与适配 | ✅ Phase 1 |
| 关系推断 | 显式外键 + 隐式关联（命名约定、字段类型匹配） | 🚧 Phase 2 |
| 可视化 | 交互式 ER 关系图 | 🚧 Phase 2 |
| AI 问答 | 用自然语言查询表结构、字段含义、关联路径 | 📅 Phase 3 |
| 文档生成 | 自动生成数据字典文档（Markdown） | 📅 Phase 3 |
| 版本对比 | DDL 版本差异高亮对比 | 📅 Phase 4 |

## 技术栈

| 层 | 技术选型 |
|----|---------|
| 后端框架 | FastAPI (Python) |
| SQL 解析 | [sqlglot](https://github.com/tobymao/sqlglot) — 支持多种 SQL 方言 |
| AI SDK | Anthropic Claude API |
| 存储 | SQLite（开发）/ PostgreSQL（生产） |
| 前端 | React + vis-network / D3.js |
| 包管理 | pipx + venv |

## 快速开始

### 环境要求

- Python 3.12+
- pipx（推荐）或 pip

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd ai-sql-agent

# 使用 pipx 安装依赖到 fastapi venv
pipx inject fastapi -r backend/requirements.txt
```

### 启动

```bash
cd backend
pipx run --venv fastapi uvicorn app.main:app --port 8199 --reload
```

API 文档地址：`http://localhost:8199/docs`

### 运行测试

```bash
cd backend
pipx run --venv fastapi pytest tests/ -v
```

## 项目结构

```
ai-sql-agent/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 应用入口
│   │   ├── config.py         # 配置管理
│   │   ├── api/              # API 路由
│   │   ├── models/           # Pydantic 数据模型
│   │   ├── parser/           # SQL 解析引擎
│   │   │   ├── base.py       # 解析器基类
│   │   │   ├── models.py     # 解析结果模型
│   │   │   └── dialect.py    # 方言检测
│   │   └── schemas/          # 请求/响应 Schema
│   ├── tests/                # 单元测试
│   └── requirements.txt
├── prd/                      # 产品需求文档
├── specs/                    # 规范文档（SDD）
│   ├── changes/              # 活跃变更提案
│   └── archived/             # 已归档变更
├── src/                      # 前端源码（待建设）
└── CLAUDE.md                 # 项目规范（AI 协作契约）
```

## 开发规范

本项目遵循 **SDD（Specification-Driven Development）** 规范驱动开发范式：

```
Specify → Plan → Tasks → Implement
```

每个变更依次经过四个阶段，每阶段需人工 Review 后方可继续。详见 `CLAUDE.md`。

## 路线图

| Phase | 内容 | 时间 |
|-------|------|------|
| Phase 1 | 核心解析引擎（DDL 解析、方言检测、基础 API） | 进行中 |
| Phase 2 | 关系增强 + 可视化（隐式推断、ER 图、Mermaid 导出） | 待开始 |
| Phase 3 | AI 集成（关系补全、自然语言查询、文档生成） | 待开始 |
| Phase 4 | 增强功能（多文件、版本对比、团队协作） | 待开始 |

## 许可证

MIT
