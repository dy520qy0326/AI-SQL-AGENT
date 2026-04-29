---
name: 08-dark-mode-plan
title: 暗色模式 — 技术方案
status: REVIEWED
created: 2026-04-29
---

## 架构影响分析

### 影响范围

| 模块 | 影响类型 | 说明 |
|------|----------|------|
| `globals.css` | 修改 | 新增 Tailwind v4 dark variant + transition 基础样式 |
| `Layout.tsx` | 修改 | 新增 dark mode 切换按钮 + 背景/容器 dark 样式 |
| **全部 20+ 组件/页面** | 修改 | 逐个添加 `dark:` 变体颜色类 |
| 新增 `useTheme` hook | 新增 | 管理 theme 状态、localStorage 读写、系统偏好监听 |
| `main.tsx` | 修改 | 初始化时读取 theme 并设置 `<html class="dark">` |

### 风险点

| 风险 | 缓解 |
|------|------|
| 暗色下 ER 图（canvas 渲染）不可见 | 反色或调色盘变暗；通过 CSS 滤镜或 ForceGraph 配置处理 |
| Mermaid 图表暗色渲染 | Mermaid 支持 `theme: 'dark'` 配置，需在渲染时动态传入 |
| 遗漏部分组件的 `dark:` 样式 | 人工全面走查，逐组件验证 |
| Tailwind v4 的 dark variant 默认跟随系统 | 需用 `@custom-variant dark` 改为 class 策略 |

## 实现方案

### Tailwind v4 dark variant 重置

Tailwind CSS v4 默认 `dark` variant 基于 `prefers-color-scheme`。需改为 class 策略，在 `globals.css` 中添加：

```css
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```

同时在 `<html>` 上添加 `class="transition-colors duration-200"` 实现整体颜色过渡。

### useTheme Hook

新建 `frontend/src/hooks/useTheme.ts`，职责：

| 能力 | 实现 |
|------|------|
| 读取偏好 | localStorage `theme` 键，值 `'light'` / `'dark'` / `'system'` |
| 系统偏好监听 | `matchMedia('(prefers-color-scheme: dark)')` change 事件 |
| 应用主题 | 设置 `document.documentElement.classList.toggle('dark', ...)` |
| 暴露接口 | `{ theme: 'light'|'dark'|'system', resolved: 'light'|'dark', setTheme, toggle }` |
| 过渡控制 | 切换时给 `<html>` 短暂添加 `transition-colors duration-200` |

初始化加载流程：
1. 读取 localStorage `theme`
2. 若无值 → `'system'`，根据 `prefers-color-scheme` 决定是否加 `dark` class
3. 若为 `'light'` / `'dark'` → 直接应用
4. 注册系统偏好 change 事件（仅在 `'system'` 模式下响应）

### 切换 UI

Layout header 右上方新增切换按钮，使用 `Sun` / `Moon` 图标（lucide-react 已安装）：

- 点按切换 `light` ↔ `dark`（设置 localStorage 为 `'light'` / `'dark'`）
- 悬停提示 "切换暗色模式" / "切换亮色模式"

### 组件 dark 样式改造规则

每个 Tailwind 颜色类按以下 pattern 添加 `dark:` 变体：

| 亮色 | 暗色 |
|------|------|
| `bg-white` | `dark:bg-gray-900` |
| `bg-gray-50` | `dark:bg-gray-950` |
| `text-gray-900` | `dark:text-gray-100` |
| `text-gray-700` | `dark:text-gray-300` |
| `text-gray-500` | `dark:text-gray-400` |
| `text-gray-400` | `dark:text-gray-500` |
| `border-gray-300` | `dark:border-gray-600` |
| `border-gray-200` | `dark:border-gray-700` |
| `bg-black/50`（遮罩） | `dark:bg-black/70` |

特殊处理：
- **ER 图**（`react-force-graph-2d`）：检测暗色模式，设置 `backgroundColor: '#1f2937'`，调整节点/文字颜色
- **Mermaid 图**：渲染时传入 `theme: 'dark'` 或 `theme: 'base'` + 暗色变量
- **Markdown 内容**：代码块、引用块等需额外 `dark:` 样式
- **CodeMirror 编辑器**：需动态设置 editor theme（light/dark）

### 工作量估算

| 阶段 | 文件数 | 预计改动量 |
|------|--------|------------|
| 基础设施（hook + css + main.tsx） | 3 | 小 |
| Layout + NavTabs + 通用组件 | 4-5 | 中 |
| 页面组件（~10 pages） | 10 | 大 |
| 子组件（~10 components） | 10 | 中 |
| ER 图 / Mermaid 适配 | 2 | 中 |
| 总计 | ~28 个文件 | 中等规模 |

## 验证方案

- 人工逐页截图对比亮/暗色
- ER 图/Mermaid 在两种模式下均可正常渲染
- 切换后刷新页面，偏好保持
- 修改系统偏好后首次进入，跟随正确
