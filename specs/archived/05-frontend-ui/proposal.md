---
name: 05-frontend-ui
title: Phase 5 — 前端 UI 开发 (Frontend User Interface)
status: ARCHIVED
created: 2026-04-29
---

## 摘要

在 Phase 1-4 完整后端能力的基础上，构建现代化前端 UI，将 SQL 解析、关系可视化、AI 问答、文档生成、版本对比等功能转化为直观的图形界面。用户无需 API 调用即可完整使用系统。

## 动机

当前系统所有功能均可通过 Swagger 文档调用，但缺乏面向最终用户的界面。在一个真实团队环境中，不同角色的使用者（后端开发、数据分析师、技术管理者）需要：

- **上传 SQL**：拖拽上传 DDL 文件并立即看到解析结果
- **浏览结构**：不读 SQL 就可以浏览所有表、字段、索引、外键
- **查看关系图**：交互式 ER 图，缩放、拖拽、筛选
- **AI 问答**：像聊天一样问数据库结构问题
- **生成文档**：一键生成数据字典，在线预览和下载
- **版本对比**：两版本间的差异可视化

前端不是后端的附属，而是后端能力的完整展现层。

## 范围

### 包含

**P0 — 核心页面（5 个页面，覆盖全流程）**

| 页面 | 功能 |
|------|------|
| 项目列表 | 创建项目、搜索、分页列表、删除 |
| 项目详情 / SQL 上传 | SQL 编辑器/文件上传、解析结果概览、统计面板 |
| 表结构浏览 | 表格视图浏览所有表、点击进入表详情（字段/索引/外键） |
| 关系视图（ER 图） | 交互式 force-directed graph 或 D3.js 关系图 |
| AI 对话 | 流式聊天界面、会话管理、消息历史 |

**P1 — 辅助页面**

| 页面 | 功能 |
|------|------|
| 文档管理 | 生成/列表/预览/下载 Markdown 数据字典 |
| 版本管理 | 版本列表、创建新版本、删除版本 |
| 差异对比 | 版本选择 → 差异概览 → 逐项展开 → breaking change 高亮 |
| 关系列表 | Tabular 视图浏览所有关系（可筛选类型/置信度） |
| AI 面板 | AI 关系补全、注释补全触发、状态查看、缓存管理 |

**P2 — 增强体验**

| 功能 | 说明 |
|------|------|
| 响应式布局 | 适配桌面和部分平板尺寸 |
| 深色模式 | CSS 变量方案，支持亮/暗切换 |
| 导出 Mermaid | 点击复制 Mermaid ER 图文本 |
| 迁移 SQL 一键复制 | diff 详情页复制 ALTER TABLE 脚本 |

### 不包含

- 用户认证 / 权限系统（单用户桌面级应用）
- PWA / 离线支持
- 多语言国际化（i18n）
- E2E 测试（单元测试 + 组件测试覆盖即可）
- 后端改造（尽量复用现有 API，不做前端驱动的后端改造）

## 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | React 18 + TypeScript | 生态成熟、类型安全 |
| 构建 | Vite | 快速 HMR，零配置启动 |
| 路由 | React Router v6 | SPA 路由标准方案 |
| 状态管理 | React Query (TanStack Query) | 服务端状态缓存、loading/error 处理 |
| HTTP 客户端 | fetch（封装一层） | 无需额外依赖 |
| 关系图 | D3.js + react-force-graph-2d | 交互式 force-directed graph |
| 样式 | Tailwind CSS | 快开、Utility-first |
| UI 组件 | shadcn/ui (Radix Primitives) | 高质量、无障碍、可定制 |
| 编辑器 | CodeMirror 6 (SQL 高亮) | SQL 语法高亮、轻量 |
| 图标 | Lucide React | 轻量、一致性高 |

## 页面设计

### 1. 项目列表页 `/projects`

```
┌─────────────────────────────────────────────┐
│  AI SQL Agent                    [+ 新建项目] │
├─────────────────────────────────────────────┤
│  [搜索框.................................................] │
├─────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ 电商系统  │ │ 物流平台  │ │ 支付中台  │  ...  │
│  │ 15 张表   │ │ 8 张表   │ │ 23 张表  │       │
│  │ 23 关系   │ │ 12 关系  │ │ 40 关系  │       │
│  │ 2026-04  │ │ 2026-03  │ │ 2026-02  │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                               ← Page 1/3 →   │
└─────────────────────────────────────────────┘
```

### 2. 项目详情 / SQL 上传 `/projects/:id`

```
┌─────────────────────────────────────────────┐
│  ← 项目列表  │  电商系统                      │
│  [上传 SQL] [表结构] [关系图] [AI] [文档] [版本]  │
├─────────────────────────────────────────────┤
│  ┌──────────────────────────────┐           │
│  │ 📄 拖拽 SQL 文件到此处       │           │
│  │    或点击选择文件             │           │
│  └──────────────────────────────┘           │
│  ┌──────────────────────────────────────────┐│
│  │  统计面板：15 张表 · 23 关系 · ...      ││
│  └──────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

### 3. 表结构浏览 `/projects/:id/tables`

```
┌─────────────────────────────────────────────┐
│  [搜索表...]                     [schema 筛选 ▼] │
├─────────────────────────────────────────────┤
│  表名          │ 字段数 │ 注释               │
│  ───────────────────────────────────────     │
│  users         │ 8      │ 用户表             │
│  orders        │ 12     │ 订单表             │
│  order_items   │ 6      │ 订单明细           │
│  products      │ 5      │ 商品表             │
│  ...                                         │
├─────────────────────────────────────────────┤
│  [点击某行展开详情]                          │
│  ┌─ users ────────────────────────────────┐ │
│  │ # │ 字段名      │ 类型    │ NULL│ PK │ 注释│ │
│  │ 1 │ id          │ bigint │ NO  │ ✅ │ 主键 │ │
│  │ 2 │ name        │ varchar │ NO  │    │ 用户名│ │
│  │ 3 │ email       │ varchar │ NO  │    │ 邮箱 │ │
│  │ ...                                     │ │
│  │ 索引: idx_email (UNIQUE)                │ │
│  │ 外键: -                                │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 4. 关系图 `/projects/:id/graph`

```
┌─────────────────────────────────────────────┐
│  [筛选: 全部/外键/推断/AI]  [置信度 ≥ 0.5 ▼]  │
├─────────────────────────────────────────────┤
│                                             │
│        ┌──────┐      ┌────────┐            │
│    ┌──→│ users│←─────│ orders │←──┐        │
│    │   └──────┘      └────────┘   │        │
│    │       ↑              ↑       │        │
│  ┌─┴──┐  ┌─┴──┐  ┌────────┐  ┌──┴──┐     │
│  │addr│  │cart│  │payment│  │items│        │
│  └────┘  └────┘  └────────┘  └─────┘      │
│                                             │
│  [拖拽节点 · 滚轮缩放 · 悬停高亮关联]        │
│                                             │
│  图例: ━ 外键  ┅ 推断  ┈ AI 建议              │
├─────────────────────────────────────────────┤
│  [📋 复制 Mermaid]                           │
└─────────────────────────────────────────────┘
```

### 5. AI 对话 `/projects/:id/ai`

```
┌─────────────────────────────────────────────┐
│  ← 项目  │  AI 对话                      │  │
├─────────────────────────────────────────────┤
│  ┌─ 会话侧栏 ───┐ ┌─ 对话区域 ─────────────┐│
│  │ 💬 新对话     │ │                        ││
│  │ ──────────   │ │  AI: 电商系统包含 15 张 ││
│  │ 对话 1       │ │  表，核心表为 ...        ││
│  │ 对话 2       │ │                        ││
│  │ 对话 3       │ │  建议问题:             ││
│  │              │ │  · 用户表和订单表的关系  ││
│  │              │ │  · 有哪些表用了 user_id  ││
│  │              │ │                        ││
│  │              │ │ ┌────────────────────┐ ││
│  │              │ │ │ user 和 order 什么  │ ││
│  │              │ │ │ 关系？             │ ││
│  │              │ │ └────────────────────┘ ││
│  │              │ │  AI: users 和 orders   ││
│  │              │ │  通过 user_id 关联...  ││
│  │              │ │  [继续输入...]  🚀     ││
│  └──────────────┘ └────────────────────────┘│
├─────────────────────────────────────────────┤
│  (SSE 流式输出，打字机效果)                  │
└─────────────────────────────────────────────┘
```

### 6. 文档管理 `/projects/:id/docs`

```
┌─────────────────────────────────────────────┐
│  [生成文档]  [☑ AI 增强]                     │
├─────────────────────────────────────────────┤
│  标题                   │ 类型  │ AI  │ 时间 │
│  电商系统 数据字典       │ MD    │ ✅  │ ... │
│  电商系统 数据字典 (增强) │ MD    │ ✅  │ ... │
├─────────────────────────────────────────────┤
│  [点击预览]                                  │
│  ┌─ Markdown 预览 ──────────────────────┐  │
│  │ # 数据字典 - 电商系统                  │  │
│  │                                       │  │
│  │ ## 表结构详情                         │  │
│  │                                       │  │
│  │ ### users                             │  │
│  │ | # | 字段 | 类型 | ... |             │  │
│  │ ────────────────────────────────────  │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│  [📋 复制]  [💾 下载]                       │
└─────────────────────────────────────────────┘
```

### 7. 版本对比 `/projects/:id/versions`

```
┌─────────────────────────────────────────────┐
│  版本列表  │  创建新版本                       │
├─────────────────────────────────────────────┤
│  Tag  │  表数  │  Hash  │  时间             │
│  v1.0 │  15    │  a3b.. │  2026-04-29      │
│  v1.1 │  17    │  c4d.. │  2026-04-29      │
│  v2.0 │  20    │  e5f.. │  2026-04-29      │
├─────────────────────────────────────────────┤
│  选择两个版本进行对比                         │
│  [旧: v1.0 ▼]  ↔  [新: v2.0 ▼]  [对比]    │
├─────────────────────────────────────────────┤
│  差异概览：+3 表  +20 字段  -2 索引  -1 关系 │
│  ⚠ 3 项破坏性变更                           │
│                                             │
│  ┌─ 表级差异 ───────────────────────────┐  │
│  │  ✅ payment_logs (新增)              │  │
│  │  ❌ old_orders (删除)                │  │
│  │  🔄 users → users_v2 (重命名)        │  │
│  └──────────────────────────────────────┘  │
│  ┌─ 字段差异 (展开) ───────────────────┐   │
│  │  orders.total_amount                │   │
│  │    int  →  bigint  🔴 BREAKING     │   │
│  │  orders.discount_old (删除) 🔴      │   │
│  └──────────────────────────────────────┘  │
│  [🤖 AI 摘要]  [📋 复制 Migration SQL]     │
└─────────────────────────────────────────────┘
```

## 技术架构

### 目录结构

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx              # 入口
    ├── App.tsx                # 路由配置 + 布局
    ├── lib/
    │   ├── api.ts             # API 客户端封装
    │   └── utils.ts           # 工具函数
    ├── types/
    │   ├── project.ts         # TypeScript 类型定义
    │   ├── table.ts
    │   ├── relation.ts
    │   ├── graph.ts
    │   ├── diff.ts
    │   ├── doc.ts
    │   └── session.ts
    ├── hooks/
    │   ├── useProjects.ts     # React Query hooks
    │   ├── useTables.ts
    │   ├── useRelations.ts
    │   ├── useGraph.ts
    │   ├── useAI.ts
    │   ├── useAsk.ts
    │   ├── useDocs.ts
    │   └── useVersions.ts
    ├── pages/
    │   ├── ProjectList.tsx
    │   ├── ProjectDetail.tsx
    │   ├── TablesView.tsx
    │   ├── TableDetail.tsx
    │   ├── GraphView.tsx
    │   ├── AiChat.tsx
    │   ├── DocsView.tsx
    │   ├── DocPreview.tsx
    │   ├── VersionsView.tsx
    │   └── DiffView.tsx
    ├── components/
    │   ├── Layout.tsx            # 全局布局
    │   ├── NavTabs.tsx           # 项目内 tab 导航
    │   ├── SqlUploader.tsx       # SQL 上传组件
    │   ├── StatsPanel.tsx        # 统计面板
    │   ├── TableRow.tsx          # 表结构行
    │   ├── ErGraph.tsx           # ER 关系图组件
    │   ├── RelationFilters.tsx   # 关系筛选
    │   ├── ChatMessage.tsx       # 聊天消息
    │   ├── ChatInput.tsx         # 聊天输入
    │   ├── SessionList.tsx       # 会话列表
    │   ├── DocCard.tsx           # 文档卡片
    │   ├── VersionSelector.tsx   # 版本选择器
    │   ├── DiffList.tsx          # 差异列表
    │   └── MarkdownViewer.tsx    # Markdown 预览
    └── styles/
        └── globals.css          # Tailwind + 自定义样式
```

### API 客户端设计

```typescript
// src/lib/api.ts — 简化版
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8199";

class ApiClient {
  async get<T>(path: string): Promise<T> { ... }
  async post<T>(path: string, body?: unknown): Promise<T> { ... }
  async del(path: string): Promise<void> { ... }
  async postFormData<T>(path: string, data: FormData): Promise<T> { ... }
  async streamSSE(path: string, body: unknown, onChunk: (chunk: string) => void, signal?: AbortSignal): Promise<void> { ... }
}

export const api = new ApiClient();
```

### React Query hooks 模式

```typescript
// src/hooks/useProjects.ts
export function useProjects(page: number, size: number) {
  return useQuery({
    queryKey: ["projects", { page, size }],
    queryFn: () => api.get<ProjectListResponse>(`/api/projects?page=${page}&size=${size}`),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) => api.post("/api/projects", data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });
}
```

### 关系图交互设计

使用 `react-force-graph-2d`（基于 D3.js force layout）：

- 节点 = 表：圆形，大小表示字段数，颜色表示 schema
- 边 = 关系：不同线条样式表示不同类型（实线=外键，虚线=推断，点线=AI）
- 悬停节点：高亮关联节点和边，淡出无关节点
- 拖拽：可拖动节点调整布局
- 滚轮：缩放
- 右键：菜单（查看表详情）
- 图例：右上角，显示关系类型样式

## 路由设计

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向到 `/projects` | |
| `/projects` | ProjectList | 项目列表 |
| `/projects/:id` | ProjectDetail | 项目概览 + SQL 上传 |
| `/projects/:id/tables` | TablesView | 表结构浏览 |
| `/projects/:id/tables/:tableId` | TableDetail | 表详情 |
| `/projects/:id/graph` | GraphView | ER 关系图 |
| `/projects/:id/ai` | AiChat | AI 对话 |
| `/projects/:id/docs` | DocsView | 文档列表 |
| `/projects/:id/docs/:docId` | DocPreview | 文档预览 |
| `/projects/:id/versions` | VersionsView | 版本管理 |
| `/projects/:id/diff/:diffId` | DiffView | 差异详情 |

## 验收标准

- [ ] 新建项目 → 上传 SQL 文件 → 自动解析 → 看到解析结果（表数、关系数）
- [ ] 表结构页面展示所有表，可搜索和筛选
- [ ] 表详情页展示字段、索引、外键完整信息
- [ ] ER 关系图正确渲染节点和边，可交互（拖拽、缩放、悬停）
- [ ] 关系图根据筛选条件（类型/置信度）正确过滤
- [ ] AI 对话页：输入问题 → SSE 流式显示回答 → 会话管理
- [ ] 文档页：生成文档 → 列表展示 → 预览（Markdown 渲染）→ 下载
- [ ] 版本页：版本列表 → 选择两版本 → 差异对比页面 → breaking 高亮
- [ ] 差异详情页：可查看 AI 摘要，可复制 Migration SQL
- [ ] 响应式布局在 1920×1080 下呈现正常
- [ ] 前后端分离开发和部署，CORS 配置正确

## 备注

- 前端项目与后端分离，独立启动（`npm run dev` / `npm run build`）
- Tailwind + shadcn/ui 方案便于快速迭代
- 关系图性能：>100 节点时应启用虚拟化 / 限制初始渲染节点数
- SSE 流式响应在前端使用 `EventSource` 或 `fetch` 手动解析
- TypeScript 类型直接从后端 Pydantic schema 手动翻译，不做自动生成
