# AI SQL Agent

> 上传 SQL DDL 文件，自动解析数据库表结构并识别表间关联关系，借助 AI 能力提供可视化、智能问答和文档生成。

## 功能概览

| 功能 | 说明 | 状态 |
|------|------|------|
| SQL 解析 | 解析 `CREATE TABLE` DDL，提取表、字段、类型、约束、外键、索引 | ✅ |
| 方言支持 | MySQL、PostgreSQL 自动方言检测与适配 | ✅ |
| 关系推断 | 显式外键 + 隐式关联（命名约定、字段类型匹配）+ SQL 查询关系检测 | ✅ |
| 可视化 | 交互式 ER 关系图 + Mermaid 图表渲染 | ✅ |
| AI 问答 | 用自然语言查询表结构、字段含义、关联路径 | ✅ |
| 文档生成 | 自动生成数据字典文档（Markdown） | ✅ |
| 版本对比 | DDL 版本差异高亮对比 | ✅ |
| 暗色模式 | 支持亮色/暗色主题切换 | ✅ |

## 技术栈

| 层 | 技术选型 |
|----|---------|
| 后端框架 | FastAPI (Python) |
| SQL 解析 | [sqlglot](https://github.com/tobymao/sqlglot) — 支持多种 SQL 方言 |
| AI SDK | Anthropic Claude API |
| 存储 | SQLite |
| 前端 | React 19 + Vite + TypeScript |
| 可视化 | react-force-graph-2d + Mermaid |
| 样式 | Tailwind CSS 4 |
| 包管理 | `.venv/`（项目根目录 Python venv） |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd ai-sql-agent

# 创建 Python 虚拟环境并安装后端依赖
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 安装前端依赖
cd frontend
npm install
```

### 启动

```bash
# 后端（端口 8199）
cd backend
../.venv/bin/uvicorn app.main:app --port 8199 --reload

# 前端开发服务器（端口 5173）
cd frontend
npm run dev -- --host 0.0.0.0
```

API 文档地址：`http://localhost:8199/docs`

### 运行测试

```bash
cd backend
../.venv/bin/python -m pytest tests/ -x -q
```

## 项目结构

```
ai-sql-agent/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 应用入口
│   │   ├── config.py            # 配置管理
│   │   ├── ai/                  # AI 服务（问答、缓存、提示词）
│   │   ├── api/                 # API 路由（projects, tables, graph, ai, diff, relations, sessions）
│   │   ├── db/                  # 数据库引擎与 ORM 模型
│   │   ├── detector/            # 关系推断引擎
│   │   ├── docgen/              # 文档生成器
│   │   ├── nl/                  # 自然语言查询上下文构建
│   │   ├── parser/              # SQL 解析引擎（DDL、方言检测）
│   │   ├── schemas/             # Pydantic 请求/响应 Schema
│   │   ├── store/               # 数据访问层（Repository）
│   │   └── viz/                 # 可视化（ER 图、Mermaid 导出）
│   ├── tests/                   # 单元测试
│   ├── data/                    # SQLite 数据库文件
│   └── requirements.txt
├── frontend/                    # React 前端
│   └── src/
│       ├── components/          # 可复用组件
│       ├── hooks/               # 自定义 Hooks
│       ├── pages/               # 页面组件
│       ├── styles/              # 全局样式
│       └── types/               # TypeScript 类型定义
├── prd/                         # 产品需求文档
├── specs/                       # 规范文档（SDD）
│   ├── changes/                 # 活跃变更提案
│   └── archived/                # 已归档变更
└── CLAUDE.md                    # 项目规范（AI 协作契约）
```

## 开发规范

本项目遵循 **SDD（Specification-Driven Development）** 规范驱动开发范式：

```
Specify → Plan → Tasks → Implement
```

每个变更依次经过四个阶段，每阶段需人工 Review 后方可继续。详见 `CLAUDE.md`。

## 路线图

| 功能 | 说明 | 状态 |
|------|------|------|
| 核心解析引擎 | DDL 解析、方言检测、基础 API | ✅ 已完成 |
| 关系检测 + 可视化 | 隐式推断、ER 图、Mermaid 导出、图表筛选 | ✅ 已完成 |
| AI 智能增强 | AI 问答、自然语言查询、文档生成 | ✅ 已完成 |
| 版本对比 | DDL 版本差异高亮对比 | ✅ 已完成 |
| 前端 UI | React + Vite + TypeScript 全功能 SPA | ✅ 已完成 |
| 暗色模式 | 亮色/暗色主题切换 | ✅ 已完成 |

## 许可证

MIT
