---
name: 09-embed-mermaid-er
title: 内嵌 Mermaid ER 图渲染 — 任务分解
status: ARCHIVED
created: 2026-04-29
---

## 任务列表

### Task 1：安装 mermaid 依赖

- 执行 `npm install mermaid` 安装官方渲染包
- 交付标准：`package.json` 和 `package-lock.json` 更新

### Task 2：封装 MermaidDiagram 组件

- 新建 `frontend/src/components/MermaidDiagram.tsx`
- 组件接口：
  - `chart: string` — Mermaid 语法文本
  - `isDark?: boolean` — 暗色模式
  - `onError?: (err: Error) => void` — 渲染失败回调
- 内部逻辑：
  - `mermaid.initialize()` 在挂载时调用，设定 theme（`dark` | `default`）
  - `useEffect` 监听 `chart` 变化，调用 `mermaid.render(id, chart)` 生成 SVG
  - 前置 `mermaid.parse(chart)` 做语法校验，不合法直接走 error 状态
  - 渲染状态：loading → 渲染中 / error → 错误展示
- 交付标准：组件可独立渲染合法 Mermaid 文本为可视化 SVG

### Task 3：改造 GraphView 页面

- 变更 `frontend/src/pages/GraphView.tsx`：
  - 添加视图状态：`viewMode: 'graph' | 'mermaid'`
  - 在筛选栏右侧添加切换按钮（使用 `GitBranch` 和 `Workflow` 图标区分两种视图）
  - `viewMode === 'graph'` → 渲染现有 `ErGraph`
  - `viewMode === 'mermaid'` → 渲染 `MermaidDiagram` + 加载状态
  - Mermaid 文本通过现有的 `useMermaid` hook 获取，筛选变化时自动重新 fetch
  - 容器高度与 ErGraph 一致（h-[600px]），支持水平滚动
- 交付标准：
  - 两种视图可自由切换
  - 筛选条件（type + minConfidence）在 Mermaid 视图下生效
  - 暗色模式切换时 Mermaid 图自动刷新
  - "复制 Mermaid"按钮在两种视图下均可使用
