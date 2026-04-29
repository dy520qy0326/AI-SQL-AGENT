import { useState } from 'react'
import {
  Search,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  Table2,
  ArrowRight,
  X,
} from 'lucide-react'
import { useQueryRelations } from '@/hooks/useQueryRelations'

interface QueryRelationPanelProps {
  projectId: string
}

export function QueryRelationPanel({ projectId }: QueryRelationPanelProps) {
  const [sql, setSql] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const { preview, save } = useQueryRelations(projectId)

  const handlePreview = () => {
    if (!sql.trim()) return
    setSelectedIds(new Set())
    preview.mutate(sql)
  }

  const handleSelectAll = () => {
    if (!preview.data) return
    if (selectedIds.size === preview.data.relations.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(preview.data.relations.map((r) => r.temp_id)))
    }
  }

  const handleToggle = (tempId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(tempId)) next.delete(tempId)
      else next.add(tempId)
      return next
    })
  }

  const handleSave = () => {
    if (selectedIds.size === 0) return
    save.mutate({ sql, relation_ids: Array.from(selectedIds) })
  }

  const handleSaveAll = () => {
    if (!preview.data || preview.data.relations.length === 0) return
    const ids = preview.data.relations
      .filter((r) => !r.already_exists)
      .map((r) => r.temp_id)
    if (ids.length === 0) return
    save.mutate({ sql, relation_ids: ids })
  }

  const clearAll = () => {
    setSql('')
    setSelectedIds(new Set())
    preview.reset()
    save.reset()
  }

  const isPreviewsDisabled = !sql.trim() || preview.isPending
  const hasPreviewData = preview.data && preview.data.relations.length > 0
  const hasUnmatched =
    preview.data && preview.data.unmatched_tables.length > 0
  const hasSelectable =
    hasPreviewData && preview.data!.relations.some((r) => !r.already_exists)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">
          从 SQL 查询识别关系
        </h2>
        {(preview.data || save.data) && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer"
          >
            <X className="h-3 w-3" />
            清空
          </button>
        )}
      </div>

      {/* SQL Input */}
      <div>
        <textarea
          value={sql}
          onChange={(e) => setSql(e.target.value)}
          placeholder={`粘贴 SQL 查询语句（支持多条）\n例如：\nSELECT u.name, o.total\nFROM users u\nLEFT JOIN orders o ON u.id = o.user_id`}
          rows={6}
          className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm font-mono text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:placeholder-gray-500"
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handlePreview()
          }}
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-gray-400 dark:text-gray-500">Ctrl+Enter 预览</span>
          <button
            onClick={handlePreview}
            disabled={isPreviewsDisabled}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          >
            {preview.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            预览关系
          </button>
        </div>
      </div>

      {/* Preview Error */}
      {preview.isError && (
        <div className="flex items-start gap-2 rounded-lg border bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {preview.error instanceof Error ? preview.error.message : '解析失败'}
          </span>
        </div>
      )}

      {/* Preview Loading */}
      {preview.isPending && (
        <div className="flex items-center gap-2 rounded-lg border bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          正在解析查询语句...
        </div>
      )}

      {/* Preview Result: Empty */}
      {preview.data && preview.data.relations.length === 0 && !hasUnmatched && (
        <div className="flex items-start gap-2 rounded-lg border bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          未发现 JOIN 关系。请检查 SQL 中是否包含 JOIN 子句。
        </div>
      )}

      {/* Preview Result: Relations Table */}
      {hasPreviewData && (
        <div className="overflow-hidden rounded-lg border dark:border-gray-700">
          <div className="border-b bg-gray-50 px-4 py-2 text-xs font-medium text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
            发现 {preview.data!.relations.length} 个关系
            {preview.data!.queries_parsed > 1 &&
              `（解析 ${preview.data!.queries_parsed} 条语句）`}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-medium text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
                  <th className="w-10 px-3 py-2">
                    <input
                      type="checkbox"
                      checked={
                        preview.data!.relations.length > 0 &&
                        selectedIds.size === preview.data!.relations.length
                      }
                      onChange={handleSelectAll}
                      className="h-4 w-4 cursor-pointer rounded border-gray-300"
                    />
                  </th>
                  <th className="px-3 py-2">源表</th>
                  <th className="px-3 py-2">关联列</th>
                  <th className="px-3 py-2" />
                  <th className="px-3 py-2">目标表</th>
                  <th className="px-3 py-2">关联列</th>
                  <th className="px-3 py-2">JOIN 类型</th>
                  <th className="px-3 py-2">状态</th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-gray-700">
                {preview.data!.relations.map((rel) => (
                  <tr
                    key={rel.temp_id}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-800/50 ${rel.already_exists ? 'opacity-50' : ''}`}
                  >
                    <td className="px-3 py-2.5">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(rel.temp_id)}
                        onChange={() => handleToggle(rel.temp_id)}
                        disabled={rel.already_exists}
                        className="h-4 w-4 cursor-pointer rounded border-gray-300 disabled:cursor-not-allowed disabled:opacity-30"
                      />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-medium text-gray-800 dark:text-gray-200">
                      <span className="inline-flex items-center gap-1">
                        <Table2 className="h-3.5 w-3.5 text-blue-500" />
                        {rel.source_table}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-gray-600 dark:text-gray-400">
                      {rel.source_columns.join(', ')}
                    </td>
                    <td className="px-3 py-2.5 text-gray-400">
                      <ArrowRight className="h-3.5 w-3.5" />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-medium text-gray-800 dark:text-gray-200">
                      <span className="inline-flex items-center gap-1">
                        <Table2 className="h-3.5 w-3.5 text-green-500" />
                        {rel.target_table}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-gray-600 dark:text-gray-400">
                      {rel.target_columns.join(', ')}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-xs text-gray-500 dark:text-gray-400">
                      <span className="rounded bg-gray-100 px-2 py-0.5 font-medium dark:bg-gray-700 dark:text-gray-300">
                        {rel.join_type}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-xs">
                      {rel.already_exists ? (
                        <span className="text-gray-400">已存在</span>
                      ) : (
                        <span className="text-green-600 dark:text-green-400">新发现</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unmatched Tables */}
      {hasUnmatched && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800 dark:bg-amber-950">
          <p className="mb-1 text-xs font-medium text-amber-800 dark:text-amber-200">
            以下表不在当前项目中（无法保存关联）
          </p>
          <div className="flex flex-wrap gap-1.5">
            {preview.data!.unmatched_tables.map((t) => (
              <span
                key={t}
                className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900 dark:text-amber-300"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Save Actions */}
      {hasPreviewData && (
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={selectedIds.size === 0 || save.isPending}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          >
            {save.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            保存选中 ({selectedIds.size})
          </button>
          {hasSelectable && (
            <button
              onClick={handleSaveAll}
              disabled={save.isPending}
              className="flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 cursor-pointer disabled:opacity-50"
            >
              保存全部新关系
            </button>
          )}
        </div>
      )}

      {/* Save Result */}
      {save.isPending && (
        <div className="flex items-center gap-2 rounded-lg border bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          正在保存关系...
        </div>
      )}

      {save.isError && (
        <div className="flex items-start gap-2 rounded-lg border bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{save.error instanceof Error ? save.error.message : '保存失败'}</span>
        </div>
      )}

      {save.data && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 rounded-lg border bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
            <CheckCircle className="h-4 w-4" />
            保存完成：新增 {save.data.saved} 个关系
            {save.data.skipped > 0 && `，跳过 ${save.data.skipped} 个已存在的关系`}
          </div>
          {save.data.relations.length > 0 && (
            <div className="overflow-hidden rounded-lg border dark:border-gray-700">
              <div className="border-b bg-gray-50 px-4 py-2 text-xs font-medium text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
                已保存的关系
              </div>
              <div className="divide-y dark:divide-gray-700">
                {save.data.relations.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
                  >
                    <CheckCircle className="h-3.5 w-3.5 shrink-0 text-green-500" />
                    <span className="font-medium">{r.source_table}</span>
                    <span className="font-mono text-xs text-gray-400">
                      ({r.source_columns.join(', ')})
                    </span>
                    <ArrowRight className="h-3 w-3 text-gray-400" />
                    <span className="font-medium">{r.target_table}</span>
                    <span className="font-mono text-xs text-gray-400">
                      ({r.target_columns.join(', ')})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
