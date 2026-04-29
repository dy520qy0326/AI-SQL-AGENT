---
name: 09-embed-mermaid-er
title: 内嵌 Mermaid ER 图渲染 — 技术方案
status: REVIEWED
created: 2026-04-29
---

## 架构影响分析

### 变更范围

本次变更全部集中在前端，后端无改动。

```
frontend/src/
├── components/
│   └── MermaidDiagram.tsx    # [新增] Mermaid 文本 → SVG 渲染组件
├── pages/
│   └── GraphView.tsx          # [修改] 加视图切换 + 嵌入 Mermaid 图
```

### 依赖变更

- 新增 npm 包：`mermaid` ^11.x（官方渲染引擎，~500KB gzip 后约 120KB）

### 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| mermaid 包体积较大 | 首次加载耗时增加 | 使用 `mermaid` 的运行时加载 + 懒加载组件 |
| 大图渲染性能 | 50+ 表时 SVG DOM 节点多 | 使用 `mermaid.render()` 异步 API，不阻塞主线程 |
| Mermaid 语法错误 | 空白区域 | 先 `mermaid.parse()` 预校验，失败展示错误提示 |

## 实现路径

### Step 1：安装 mermaid 包

```bash
npm install mermaid
```

### Step 2：封装 MermaidDiagram 组件

新建 `frontend/src/components/MermaidDiagram.tsx`：

- 接收 `chart: string` 属性（Mermaid 语法文本）
- 使用 `useEffect` 监听 `chart` 变化，调用 `mermaid.render()` 生成 SVG
- 将生成的 SVG 通过 `dangerouslySetInnerHTML` 插入（mermaid 官方做法）
- 渲染状态管理：loading → ready / error
- 暗色模式：`mermaid.initialize({ theme: isDark ? 'dark' : 'default' })` 在组件挂载和主题切换时调用
- 清理：组件卸载时调用 `mermaid.destroy()` 或重置

组件接口设计：
```typescript
interface MermaidDiagramProps {
  chart: string
  isDark?: boolean
  onError?: (error: Error) => void
}
```

### Step 3：改造 GraphView 页面

在 `frontend/src/pages/GraphView.tsx` 中：

1. 导入 `MermaidDiagram` 组件
2. 添加视图切换状态：`viewMode: 'graph' | 'mermaid'`
3. 在筛选栏右侧添加切换按钮组（两个图标按钮）
4. 根据 `viewMode` 条件渲染：
   - `'graph'` → 现有的 `ErGraph`
   - `'mermaid'` → `MermaidDiagram`（使用 `useMermaid` hook 返回的文本）
5. 两种视图共享同一套筛选条件（type + minConfidence），切换时自动应用

### Step 4：微调与测试

- 确保 Mermaid 图容器高度与力导向图一致（h-[600px]）
- 确保复制 Mermaid 按钮在两种视图下均可用
- 暗色模式切换时 Mermaid 图即时刷新
- 大图测试：用 sample_20_tables.sql 上传后切换视图验证

## 工作量估算

| 步骤 | 工作量 |
|------|--------|
| Step 1 安装依赖 | ~1 min |
| Step 2 MermaidDiagram 组件 | ~20 min |
| Step 3 GraphView 改造 | ~15 min |
| Step 4 微调与验证 | ~10 min |
| **合计** | **~45 min** |

## 关键设计决策

### 为什么用 `dangerouslySetInnerHTML`？

mermaid.render() 返回的是 SVG 字符串，React 默认会转义 HTML。mermaid 官方推荐的集成方式就是通过 innerHTML 插入 SVG，因为 SVG 中可能包含 `<style>`、`<defs>` 等标签，React 的 JSX 渲染会丢失这些内容。Mermaid 生成的 SVG 是纯展示性的，没有 XSS 风险。

### 为什么视图切换不添加路由参数？

简单的本地状态就够了，没有必要污染 URL。用户不太可能直接分享某个视图状态的链接。
