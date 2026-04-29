---
name: 05-frontend-ui-plan
title: Phase 5 — 前端 UI 开发 (技术方案)
status: REVIEWED
created: 2026-04-29
---

## 1. 架构概览

前后端分离架构，前端独立开发/部署，通过 HTTP API 与 FastAPI 后端通信。

```
┌──────────────────────────────────────────────┐
│                 Browser                       │
│  ┌──────────────────────────────────────────┐│
│  │         React SPA (Vite)                 ││
│  │  ┌─────┐ ┌──────┐ ┌──────┐ ┌──────────┐ ││
│  │  │Router│ │R.Query│ │force │ │ SSE      │ ││
│  │  │ v6   │ │Cache  │ │graph │ │ Stream   │ ││
│  │  └──┬──┘ └──┬───┘ └──┬───┘ └────┬─────┘ ││
│  │     └────────┼────────┼──────────┘        ││
│  │              ▼        ▼                   ││
│  │       ┌──────────────┐                    ││
│  │       │  API Client (fetch)              ││
│  │       └──────┬───────┘                    ││
│  └──────────────┼───────────────────────────┘│
└─────────────────┼────────────────────────────┘
                  │ HTTP / SSE
┌─────────────────┼────────────────────────────┐
│  FastAPI Backend (port 8199)                 │
│  /api/*                                       │
└──────────────────────────────────────────────┘
```

## 2. 项目初始化

### 创建方式

使用 Vite + React + TypeScript 模板手动搭建（不使用 create-next-app 等重型脚手架）。

### 关键依赖版本

| 包 | 用途 | 备注 |
|----|------|------|
| react@19 + react-dom@19 | UI 框架 | |
| react-router@7 | 路由 | |
| @tanstack/react-query@5 | 服务端状态 | |
| tailwindcss@4 | 样式 | Vite plugin 模式 |
| lucide-react | 图标 | |
| react-force-graph-2d | ER 关系图 | 基于 D3.js |
| codemirror@6 + @codemirror/lang-sql | SQL 编辑器 | |
| react-markdown + remark-gfm | Markdown 渲染 | |
| clsx + tailwind-merge | cn() 工具 | |
| shadcn/ui 组件 | UI 基座 | 按需安装 |

### Vite 配置要点

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8199",  // 开发代理
      "/health": "http://localhost:8199",
    },
  },
});
```

## 3. 路由与布局

### 路由层次

```
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Navigate to="/projects" />} />
    <Route path="/projects" element={<ProjectList />} />
    <Route path="/projects/:id" element={<ProjectLayout />}>
      <Route index element={<ProjectDetail />} />
      <Route path="tables" element={<TablesView />} />
      <Route path="tables/:tableId" element={<TableDetail />} />
      <Route path="graph" element={<GraphView />} />
      <Route path="ai" element={<AiChat />} />
      <Route path="docs" element={<DocsView />} />
      <Route path="docs/:docId" element={<DocPreview />} />
      <Route path="versions" element={<VersionsView />} />
      <Route path="diff/:diffId" element={<DiffView />} />
    </Route>
  </Routes>
</BrowserRouter>
```

### 布局组件

- **ProjectLayout** 包含顶部 Tabs 导航（上传/表结构/关系图/AI/文档/版本）
- Tabs 使用 `useParams()` 驱动，URL 改变自动切换
- 所有项目子页面共享同一个 React Query `queryKey: ["project", id]` 的 project 信息

## 4. 数据流设计

### API Client 层

```typescript
// src/lib/api.ts
// 封装 fetch，统一处理：
// - 请求/响应序列化
// - 错误码映射（401/403/404/422/500）
// - SSE stream 手动解析

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API Error ${status}: ${detail}`);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? JSON.stringify(body));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// SSE stream
async function streamSSE(
  path: string,
  body: unknown,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        if (data.type === "chunk") onChunk(data.content);
        if (data.type === "error") throw new Error(data.message);
      }
    }
  }
}
```

### React Query 策略

- **queryKey 命名规范**：`[resource, params]` 如 `["projects", { page, size }]`, `["tables", projectId]`
- **staleTime**：项目列表 30s，表结构 5min（schema 变化频率低）
- **gcTime**：默认 5min
- **突变后失效**：上传 SQL 后失效 `["tables", projectId]`, `["graph", projectId]` 等
- **AI 接口不缓存**：`POST` 请求，使用 `useMutation` 而非 `useQuery`

### 错误处理

- API Client 统一捕获并包装为 `ApiError`
- React Query 的 `onError` 全局 toast 通知
- SSE stream 错误显示在聊天界面中
- 各页面兜底展示错误状态 + 重试按钮

## 5. 关键组件设计

### SQL 上传 (SqlUploader)

```
两种模式：
┌─ Tab: 文件上传 ─────────────────────────────┐
│  drag & drop zone（接受 .sql 文件）           │
│  → FileReader 读取内容 → POST upload API     │
│  → 成功后跳转到表结构页                        │
└─────────────────────────────────────────────┘

┌─ Tab: 编辑器 ───────────────────────────────┐
│  CodeMirror 6 + sql 语法高亮                  │
│  → 粘贴 SQL → Ctrl+Enter / 按钮提交          │
└─────────────────────────────────────────────┘
```

### ER 关系图 (ErGraph)

使用 `react-force-graph-2d`，数据来源 `GET /api/projects/:id/graph`。

```typescript
interface GraphNode {
  id: string;
  name: string;
  columnCount: number;
  schemaName?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: "FOREIGN_KEY" | "INFERRED" | "AI_SUGGESTED";
  confidence: number;
}
```

交互设计：
- 默认 force layout，节点自动排布
- 节点颜色：按 schema 分组，单 schema 都用同色
- 节点大小：按字段数比例
- 边样式：实线（外键） / 虚线（推断） / 点线（AI）
- 悬停节点：高亮关联节点 + 边，其余淡出（opacity 0.1）
- 拖拽节点：固定位置（d.fx, d.fy），双击释放
- 滚轮缩放
- 右上角图例

筛选控制：
- 关系类型 dropdown（全部/外键/推断/AI）
- 置信度滑块 (0.0 ~ 1.0)

### AI 对话 (AiChat)

```typescript
interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { table: string; column?: string; description?: string }[];
  created_at: string;
}
```

实现要点：
- 左侧会话列表（`GET /api/projects/:id/sessions`）
- 右侧消息区域（`GET /api/sessions/:id/messages`）
- 输入框提交 → `POST /api/projects/:id/ask`（SSE stream）
- 流式响应逐步追加到当前消息气泡中（打字机效果）
- 新对话自动创建 session
- 对话历史本地无缓存，每次从后端加载
- 滚动到底部跟随（auto-scroll），用户回看时暂停跟随

### 差异对比 (DiffView)

状态管理：
```
版本列表加载 → 用户选择旧/新版本
  → POST /api/projects/:id/diff 创建 diff
  → 获取 diff_data → 渲染差异视图
```

差异渲染策略：
- 顶层统计徽章：+N 表 / -M 表 / ±字段 / ±索引 / ±关系 / ⚠ breaking
- 所有差异列表支持展开/折叠
- breaking change 用红色标记 + ⚠ 图标
- 字段修改使用 before → after 对比表格
- 嵌入 AI 摘要区域（点击生成，加载态，结果显示）
- 嵌入 Migration SQL 区域（点击生成，代码高亮显示 + 复制按钮）

## 6. TypeScript 类型定义

手动从后端 Pydantic schema 翻译，核心类型定义在 `src/types/` 下。

### 项目类型

```typescript
export interface Project {
  id: string;
  name: string;
  description?: string;
  dialect?: string;
  table_count: number;
  relation_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  dialect?: string;
}

export interface UploadResponse {
  tables_count: number;
  relations_count: number;
  errors: { statement_index: number; line: number; message: string }[];
}
```

### 表类型

```typescript
export interface TableSummary {
  id: string;
  name: string;
  schema_name?: string;
  comment?: string;
  column_count: number;
  created_at: string;
}

export interface Column {
  id: string;
  name: string;
  data_type: string;
  length?: number;
  nullable: boolean;
  default_value?: string;
  is_primary_key: boolean;
  ordinal_position: number;
  comment?: string;
}

export interface Index {
  id: string;
  name: string;
  unique: boolean;
  columns: string[];
}

export interface ForeignKey {
  id: string;
  columns: string[];
  ref_table_name: string;
  ref_columns: string[];
  constraint_name?: string;
}

export interface TableDetail extends TableSummary {
  columns: Column[];
  indexes: Index[];
  foreign_keys: ForeignKey[];
}
```

### 关系类型

```typescript
export interface Relation {
  id: string;
  source_table_id: string;
  source_table_name: string;
  source_columns: string[];
  target_table_id: string;
  target_table_name: string;
  target_columns: string[];
  relation_type: "FOREIGN_KEY" | "INFERRED" | "AI_SUGGESTED";
  confidence: number;
  source: string;
}
```

### 图类型

```typescript
export interface GraphNode {
  id: string;
  name: string;
  schema_name?: string;
  column_count: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  confidence: number;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
```

### 版本 & 差异类型

```typescript
export interface Version {
  id: string;
  project_id: string;
  version_tag: string;
  file_hash: string;
  tables_count: number;
  created_at: string;
}

export interface DiffData {
  tables_added: any[];
  tables_removed: any[];
  tables_renamed: any[];
  fields_added: any[];
  fields_removed: any[];
  fields_modified: any[];
  fields_renamed: any[];
  indexes_added: any[];
  indexes_removed: any[];
  relations_added: any[];
  relations_removed: any[];
  breaking_changes: boolean;
  breaking_details: string[];
  summary_stats: Record<string, any>;
}

export interface Diff {
  id: string;
  project_id: string;
  old_version_id: string;
  new_version_id: string;
  diff_data: DiffData;
  summary?: string;
  breaking_changes: boolean;
  created_at: string;
}
```

### 对话类型

```typescript
export interface Session {
  id: string;
  project_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { table: string; column?: string; description?: string }[];
  created_at: string;
}

export interface AskRequest {
  question: string;
  session_id?: string;
}
```

## 7. CORS 配置

后端 `app/main.py` 需添加 CORS 中间件：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 8. 开发环境

```bash
cd frontend/
npm install
npm run dev     # → localhost:5173, proxy /api → :8199
```

## 9. 实现顺序

见 `tasks.md`，按页面依赖关系依次实现。

## 10. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| react-force-graph-2d 在大型图下性能下降 | 用户体验差 | 超过 50 节点启用节点虚化，限制初始渲染 |
| SSE 流式响应用户断连 | 资源浪费 | 使用 AbortController，组件卸载时 abort |
| 后端 API 分页不一致 | 前端分页失效 | 统一使用 `page`/`size` 参数，后端返回 `total` |
| Markdown 渲染 XSS | 安全风险 | 使用 react-markdown 默认安全设置，不渲染 HTML |
| TypeScript 类型与后端不同步 | 类型错误 | 阶段性手工对齐，不引入自动生成工具 |

## 11. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE` | `http://localhost:8199` | 后端 API 地址（生产用） |
