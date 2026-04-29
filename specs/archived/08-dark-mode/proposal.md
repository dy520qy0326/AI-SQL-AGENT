---
name: 08-dark-mode
title: 暗色模式（Dark Mode）
status: ARCHIVED
created: 2026-04-29
---

## 摘要

为前端 UI 增加暗色模式（Dark Mode）支持，用户在亮色/暗色之间切换，偏好持久化到 localStorage。所有现有页面和组件均需适配。

## 动机

当前前端全部使用 Tailwind CSS 亮色配色（`bg-white`、`bg-gray-50`、`text-gray-900` 等），在低光环境下使用体验不佳。暗色模式是基础 UX 特性，用户预期现代 Web 应用默认支持。

## 范围

### 包含

- 暗色模式切换开关（Layout header 中）
- 所有现有页面/组件的暗色样式适配
  - 页面背景、卡片、表格、弹窗
  - 文本颜色层级、输入框、按钮
  - ER 图 / Mermaid 图表
  - Markdown 渲染内容
  - AI 对话气泡、上传区域
  - 分页控件、确认弹窗
  - 导航 Tab、版本选择器、Diff 视图
- 切换策略：class 策略（`<html class="dark">`），通过 `dark:` 变体控制
- 偏好持久化：localStorage + 系统 `prefers-color-scheme` 作为初始值
- 过渡动画：颜色切换时平滑过渡（`transition-colors`）

### 不包含

- 自定义主题色（非本项目范围，如需改色应单独提案）
- 暗色专属功能（如降低动画、高对比度等无障碍特性）
- 后端相关改动（纯前端变更）

### 依赖

- Tailwind CSS v3+（已内建 `dark:` variant 支持）
- 前端现有组件体系

## 规范

### 切换机制

| 条目 | 说明 |
|------|------|
| 策略 | `class` 策略，切换 `<html>` 的 `dark` class |
| 存储 | localStorage key `theme`，值 `light` / `dark` / `system` |
| 初始值 | 优先读取 localStorage；无存储时跟随 `prefers-color-scheme` |
| 切换入口 | Layout header 右上角，图标按钮（Sun/Moon 图标切换） |
| 生效范围 | 全局所有页面 |

### 配色映射

| 亮色（当前） | 暗色映射 |
|---|---|
| `bg-white` | `dark:bg-gray-800` / `dark:bg-gray-900` |
| `bg-gray-50` | `dark:bg-gray-950` |
| `text-gray-900` | `dark:text-gray-100` |
| `text-gray-700` | `dark:text-gray-300` |
| `text-gray-500` | `dark:text-gray-400` |
| `text-gray-400` | `dark:text-gray-500` |
| `border-gray-300` | `dark:border-gray-600` |
| `border-gray-200` | `dark:border-gray-700` |
| `shadow-sm` | `dark:shadow-none` / `dark:shadow-black/20` |
| `bg-blue-600` | 保持或微调（需视觉验证） |

### 过渡动画

在 `<html>` 或 `<body>` 上添加 `class="transition-colors duration-200"`，使颜色切换平滑。

### 验收标准

- [ ] Layout header 中出现暗色模式切换按钮，点击在亮/暗之间切换
- [ ] 切换后所有页面和组件正确显示暗色配色
- [ ] 刷新页面后偏好保持（localStorage）
- [ ] 首次访问时跟随系统 `prefers-color-scheme`
- [ ] 暗色模式下所有交互功能正常（上传、对话框、导航、AI 对话等）
- [ ] ER 图/Mermaid 图表在暗色模式下可读
- [ ] 切换过程带平滑过渡动画
- [ ] 无 CSS 冲突或样式泄漏

## 备注

- 纯前端改动，不涉及后端
- 本提案对应 Phase 5（前端 UI）的增强
- 切换按钮使用 `Sun` / `Moon` 图标（lucide-react 已引入）
- Dark mode 的基础设施搭建 + 组件适配可在单个 Task 内完成
