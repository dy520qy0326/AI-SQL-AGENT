---
name: 05-frontend-ui-tasks
title: Phase 5 — 前端 UI 开发 (任务分解)
status: REVIEWED
created: 2026-04-29
---

## 任务总览

| # | 任务 | 预估 | 依赖 | 页面 |
|---|------|------|------|------|
| 1 | 项目脚手架 + 项目列表页 | 1h | 无 | `/projects` |
| 2 | 项目详情 + SQL 上传 | 1h | Task 1 | `/projects/:id` |
| 3 | 表结构浏览 + 表详情 | 1.5h | Task 2 | `/projects/:id/tables` |
| 4 | ER 关系图 | 2h | Task 2 | `/projects/:id/graph` |
| 5 | AI 对话 | 2h | Task 2 | `/projects/:id/ai` |
| 6 | 文档管理 + 预览 | 1h | Task 2 | `/projects/:id/docs` |
| 7 | 版本管理 + 差异对比 | 2h | Task 2 | `/projects/:id/versions` |

**总预估**：10.5h
**关键路径**：Task 1 → 2 → 4/5/6/7（Task 3/4/5/6/7 可并行）

---

## Task 1: 项目脚手架 + 项目列表页

### 交付内容

1. Vite + React + TypeScript 项目初始化
2. Tailwind CSS 4 配置（Vite plugin 模式）
3. 全局布局组件（Layout.tsx）
4. API 客户端封装（`src/lib/api.ts`）
5. React Query 集成（`main.tsx` 中配置 QueryClientProvider）
6. 路由配置（`App.tsx`）
7. 项目列表页（`ProjectList.tsx`）
8. 后端 CORS 中间件配置

### 技术细节

**项目初始化**：
```bash
cd /mnt/e/AI-SQL-AGENT
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router@7 @tanstack/react-query@5 tailwindcss@4 @tailwindcss/vite
npm install lucide-react clsx tailwind-merge
```

**Tailwind 4 Vite 集成**：
```typescript
// vite.config.ts
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

**全局样式**（`src/styles/globals.css`）：
```css
@import "tailwindcss";
```

**API Client**（`src/lib/api.ts`）：
- 封装 GET/POST/DELETE
- 统一错误处理为 `ApiError` 类
- SSE stream 解析函数 `streamSSE`

**路由**：
```
/ → /projects 重定向
/projects → ProjectList
```

**后端 CORS**（`backend/app/main.py`）：
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], ...)
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| Layout | `src/components/Layout.tsx` | 全局布局，包含顶栏 + main |
| ProjectCard | `src/components/ProjectCard.tsx` | 项目卡片（名称、统计、时间） |
| ConfirmDialog | `src/components/ConfirmDialog.tsx` | 删除确认对话框 |

### 验收标准

- [ ] `npm run dev` 正常启动，访问 `localhost:5173` 显示页面
- [ ] 路由 `/` 自动跳转到 `/projects`
- [ ] 项目列表页展示空状态（无项目时显示提示）
- [ ] 新建项目对话框可用，调用 `POST /api/projects`
- [ ] 项目列表调用 `GET /api/projects` 并展示卡片
- [ ] 删除项目调用 `DELETE /api/projects/:id` 并确认弹窗
- [ ] 搜索项目名称功能可用
- [ ] 分页功能可用

---

## Task 2: 项目详情 + SQL 上传

### 交付内容

1. ProjectLayout 组件（顶部 Tabs 导航）
2. 项目详情概览页（StatsPanel 统计面板）
3. SQL 上传组件（文件拖拽 + CodeMirror 编辑器双模式）
4. 上传结果展示（成功/错误信息）

### 路由

```
/projects/:id → ProjectDetail（默认 tab = 概览）
其他 tabs 在后续 task 中实现
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| ProjectLayout | `src/components/ProjectLayout.tsx` | 项目内 tab 导航布局 |
| NavTabs | `src/components/NavTabs.tsx` | Tab 切换栏 |
| StatsPanel | `src/components/StatsPanel.tsx` | 统计面板（表数、关系数等） |
| SqlUploader | `src/components/SqlUploader.tsx` | SQL 上传组件 |
| ProjectDetail | `src/pages/ProjectDetail.tsx` | 项目详情页 |

### 验收标准

- [ ] 进入项目页面显示顶部导航 tabs（概览/表结构/关系图/AI/文档/版本）
- [ ] 统计面板正确显示表数量、关系数量
- [ ] SQL 上传支持拖拽 `.sql` 文件
- [ ] SQL 上传支持 CodeMirror 编辑器粘贴
- [ ] 上传成功后自动跳转到表结构页面
- [ ] 上传失败显示解析错误信息
- [ ] 新建项目对话框（复用 Task 1）

---

## Task 3: 表结构浏览 + 表详情

### 交付内容

1. 表列表页（表格视图，搜索过滤）
2. 表详情页（字段/索引/外键完整展示）
3. 行展开（inline expand）或独立详情页

### 路由

```
/projects/:id/tables → TablesView
/projects/:id/tables/:tableId → TableDetail
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| TablesView | `src/pages/TablesView.tsx` | 表列表 |
| TableDetail | `src/pages/TableDetail.tsx` | 表详情 |
| ColumnTable | `src/components/ColumnTable.tsx` | 字段表格 |
| IndexTable | `src/components/IndexTable.tsx` | 索引表格 |
| ForeignKeyTable | `src/components/ForeignKeyTable.tsx` | 外键表格 |

### 验收标准

- [ ] 表列表展示所有表名、字段数、注释
- [ ] 搜索框可过滤表名
- [ ] 点击表进入详情页
- [ ] 详情页字段表包含：序号/字段名/类型/NULL/PK/默认值/注释
- [ ] 详情页索引表包含：索引名/类型/字段列表
- [ ] 详情页外键表包含：约束名/字段/引用表/引用字段
- [ ] 无数据状态展示友好提示

---

## Task 4: ER 关系图

### 交付内容

1. ER 关系图组件（react-force-graph-2d）
2. 筛选控制（关系类型 + 置信度）
3. 节点交互（悬停高亮、拖拽、缩放）
4. 图例
5. Mermaid 文本复制按钮

### 路由

```
/projects/:id/graph → GraphView
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| GraphView | `src/pages/GraphView.tsx` | 关系图页 |
| ErGraph | `src/components/ErGraph.tsx` | 关系图组件 |
| RelationFilters | `src/components/RelationFilters.tsx` | 筛选控制面板 |
| GraphLegend | `src/components/GraphLegend.tsx` | 图例 |

### 交互设计

- `GET /api/projects/:id/graph?type=xxx&min_confidence=0.x` 获取图数据
- 筛选变化 → React Query 重新 fetch
- 节点大小 = `10 + columnCount * 2`
- 边颜色：外键=#3b82f6(蓝), 推断=#f59e0b(黄), AI=#8b5cf6(紫)
- 悬停节点：高亮边+邻居，其余节点 opacity=0.1
- 拖拽：设置 d.fx/fy，双击释放
- 显示 "加载中" / "无数据" / "后端错误" 状态

### Mermaid 文本

- `GET /api/projects/:id/mermaid` 获取原始 Mermaid 文本
- 点击复制按钮 → navigator.clipboard.writeText()
- 复制成功展示 toast

### 验收标准

- [ ] 图数据正确渲染节点和边
- [ ] 节点显示表名
- [ ] 悬停节点高亮关联节点和边
- [ ] 拖拽节点改变位置
- [ ] 滚轮缩放
- [ ] 筛选条件改变后图更新
- [ ] 图例显示正确
- [ ] 复制 Mermaid 按钮正常
- [ ] 无关系时显示空状态
- [ ] 大图（>30 节点）渲染无明显卡顿

---

## Task 5: AI 对话

### 交付内容

1. 聊天页面（左侧会话列表 + 右侧消息区域）
2. SSE 流式问答
3. 会话 CRUD
4. 建议问题

### 路由

```
/projects/:id/ai → AiChat
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| AiChat | `src/pages/AiChat.tsx` | 对话页 |
| ChatMessage | `src/components/ChatMessage.tsx` | 单条消息气泡 |
| ChatInput | `src/components/ChatInput.tsx` | 输入框 + 提交按钮 |
| SessionList | `src/components/SessionList.tsx` | 会话列表侧栏 |

### 状态管理

```typescript
// AiChat 内部状态
const [sessions, setSessions] = useState<Session[]>([]);
const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
const [messages, setMessages] = useState<Message[]>([]);
const [streamingContent, setStreamingContent] = useState("");
const [isStreaming, setIsStreaming] = useState(false);
const abortRef = useRef<AbortController | null>(null);
```

### SSE 流式逻辑

1. 用户输入 → 创建消息气泡（role=user）→ 追加到消息列表
2. 调用 `POST /api/projects/:id/ask` 开始 stream
3. 逐步追加内容到最新 assistant 气泡中
4. 收到 `done` 事件 → 完成
5. 收到 `error` 事件 → 显示错误
6. 切换会话/取消时 abort 上一个 stream

### 验收标准

- [ ] 左侧会话列表显示已有会话
- [ ] 新建会话自动创建
- [ ] 输入问题 → 流式显示 AI 回答（打字机效果）
- [ ] 切换会话加载历史消息
- [ ] 删除会话
- [ ] 会话标题自动取前 50 字
- [ ] 建议问题在空对话时显示
- [ ] 流式中的加载指示（光标闪烁）
- [ ] 长时间无响应时显示超时提示

---

## Task 6: 文档管理 + 预览

### 交付内容

1. 文档列表页
2. 生成文档（含 AI 增强开关）
3. Markdown 预览
4. 复制 / 下载

### 路由

```
/projects/:id/docs → DocsView
/projects/:id/docs/:docId → DocPreview
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| DocsView | `src/pages/DocsView.tsx` | 文档列表 |
| DocPreview | `src/pages/DocPreview.tsx` | 文档预览 |
| DocCard | `src/components/DocCard.tsx` | 文档列表项 |
| MarkdownViewer | `src/components/MarkdownViewer.tsx` | Markdown 渲染 |

### MarkdownViewer 技术选型

```typescript
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// 安全设置：不渲染 HTML tag
<ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
```

### 验收标准

- [ ] 文档列表展示已生成文档
- [ ] 点击"生成文档"调用 `POST /api/projects/:id/docs`
- [ ] AI 增强开关有效（传递 ai_enhance 参数）
- [ ] Markdown 预览渲染正常（表格、代码块、标题）
- [ ] 复制按钮复制全文到剪贴板
- [ ] 下载按钮下载为 `.md` 文件
- [ ] 删除文档

---

## Task 7: 版本管理 + 差异对比

### 交付内容

1. 版本列表页
2. 创建新版本（上传 SQL）
3. 版本选择器 → 创建 diff
4. 差异概览页面（统计 + 展开细节）
5. Breaking change 标记
6. AI 摘要生成
7. Migration SQL 导出

### 路由

```
/projects/:id/versions → VersionsView
/projects/:id/diff/:diffId → DiffView
```

### 组件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| VersionsView | `src/pages/VersionsView.tsx` | 版本管理页 |
| DiffView | `src/pages/DiffView.tsx` | 差异详情页 |
| VersionSelector | `src/components/VersionSelector.tsx` | 版本选择对比 |
| DiffList | `src/components/DiffList.tsx` | 差异条目列表 |

### 版本对比流程

```
1. 列表展示所有版本 (GET /api/projects/:id/versions)
2. 用户选择旧版 + 新版 (VersionSelector 下拉框)
3. 点击"对比" → POST /api/projects/:id/diff → 获取 diff_id
4. 跳转到 /projects/:id/diff/:diffId
5. DiffView 页面：
   a. 统计徽章（+/- 表、字段、索引、关系）
   b. 差异区块，支持展开/折叠
   c. Breaking change 红色高亮
   d. "生成 AI 摘要"按钮 → POST .../ai-summary
   e. "导出 Migration SQL"按钮 → POST .../migration
```

### 差异渲染规则

| 差异类型 | 展示方式 | 颜色 |
|---------|---------|------|
| 新增表 | 绿色 + 图标 ✅ | #16a34a |
| 删除表 | 红色 + 图标 ❌ | #dc2626 |
| 重命名表 | 橙色 + 图标 🔄 | #ea580c |
| 新增字段 | 绿色 | #16a34a |
| 删除字段 | 红色 | #dc2626 |
| 字段修改 | 蓝色 + before→after | #2563eb |
| 新增索引 | 绿色 | #16a34a |
| 删除索引 | 红色 | #dc2626 |
| Breaking | 红色 + ⚠ 图标 | #dc2626 |

### 验收标准

- [ ] 版本列表展示所有版本信息
- [ ] 创建新版本（上传 SQL）可用
- [ ] 删除版本可用
- [ ] 选择新旧版本后点击对比 → 创建 diff → 跳转
- [ ] 差异统计面板正确（数字与实际一致）
- [ ] Breaking change 正确标记
- [ ] 差异区块可展开/折叠
- [ ] 字段修改展示 before → after
- [ ] AI 摘要生成（加载态 → 显示摘要）
- [ ] Migration SQL 导出（加载态 → 显示 SQL → 可复制）
- [ ] 无差异时显示"无变更"提示
