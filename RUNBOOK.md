# 启动指南

## 一键启动（开发环境）

```bash
# 1. 后端
/mnt/e/AI-SQL-AGENT/.venv/bin/uvicorn app.main:app --port 8199

# 2. 前端（另一个终端）
npm run dev -- --host 0.0.0.0
```

打开 `http://localhost:5173/projects`。

## 失败排查清单

| 症状 | 根因 | 修复 |
|------|------|------|
| `pipx: error: unrecognized arguments: --venv` | `pipx` 没有 `--venv` 参数 | 使用 `.venv/bin/uvicorn` |
| `No module named 'fastapi'` | 系统 Python 未安装依赖 | 使用 `.venv/` 内的 Python |
| `/home/ye/.../fastapi/bin/python: No such file or directory` | pipx fastapi venv **不存在** | 使用项目 `.venv/` |
| `address already in use` | 端口 8199 已被占用 | `lsof -ti:8199 \| xargs kill` |
| `sqlite3: command not found` | 系统未安装 sqlite3 CLI | 使用 `.venv/bin/python -c "import sqlite3..."` |

## 环境验证

```bash
# 确认后端可访问
curl -s http://localhost:8199/api/projects
# 预期: {"items":[],"total":0,"page":1,"size":12}

# 确认前端可访问
curl -s http://localhost:5173 | head -c 50
# 预期: <!doctype html><html lang="zh-CN">...
```
