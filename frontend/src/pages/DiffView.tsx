import { useState } from 'react'
import { useParams, Link } from 'react-router'
import {
  ArrowLeft, Loader2, AlertCircle, AlertTriangle,
  Table2, Columns3, Hash,
  Sparkles, Copy, Check, Code,
} from 'lucide-react'
import { useDiff, useDiffAiSummary, useDiffMigration } from '@/hooks/useDiff'
import { DiffSection, AddedItem, RemovedItem, RenamedItem, ModifiedField } from '@/components/DiffList'

export function DiffView() {
  const { id, diffId } = useParams<{ id: string; diffId: string }>()
  const { data: diff, isLoading, error } = useDiff(id!, diffId!)
  const aiSummary = useDiffAiSummary(id!, diffId!)
  const migration = useDiffMigration(id!, diffId!)
  const [summaryCopied, setSummaryCopied] = useState(false)
  const [sqlCopied, setSqlCopied] = useState(false)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error || !diff) {
    return (
      <div>
        <Link to={`/projects/${id}/versions`} className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 no-underline hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <ArrowLeft className="h-4 w-4" />
          返回版本列表
        </Link>
        <div className="flex items-center gap-2 py-16 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">差异加载失败</span>
        </div>
      </div>
    )
  }

  const dd = diff.diff_data

  const handleCopySummary = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setSummaryCopied(true)
      setTimeout(() => setSummaryCopied(false), 2000)
    }).catch(() => {})
  }

  const handleCopySql = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setSqlCopied(true)
      setTimeout(() => setSqlCopied(false), 2000)
    }).catch(() => {})
  }

  return (
    <div className="space-y-6">
      <Link
        to={`/projects/${id}/versions`}
        className="inline-flex items-center gap-1 text-sm text-gray-500 no-underline hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        返回版本列表
      </Link>

      {/* Stats badges */}
      <div className="flex flex-wrap gap-3">
        {(dd.tables_added?.length > 0 || dd.tables_removed?.length > 0) && (
          <div className="flex items-center gap-1 rounded-lg border bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800">
            <Table2 className="h-4 w-4 text-gray-400" />
            <span className="text-green-600 font-medium">+{dd.tables_added?.length || 0}</span>
            <span className="text-gray-300 dark:text-gray-600">/</span>
            <span className="text-red-500 font-medium">-{dd.tables_removed?.length || 0}</span>
            <span className="text-gray-500 ml-1 dark:text-gray-400">表</span>
          </div>
        )}
        {(dd.fields_added?.length > 0 || dd.fields_removed?.length > 0 || dd.fields_modified?.length > 0) && (
          <div className="flex items-center gap-1 rounded-lg border bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800">
            <Columns3 className="h-4 w-4 text-gray-400" />
            <span className="text-green-600 font-medium">+{dd.fields_added?.length || 0}</span>
            <span className="text-gray-300 dark:text-gray-600">/</span>
            <span className="text-red-500 font-medium">-{dd.fields_removed?.length || 0}</span>
            <span className="text-gray-300 dark:text-gray-600">/</span>
            <span className="text-blue-600 font-medium">~{dd.fields_modified?.length || 0}</span>
            <span className="text-gray-500 ml-1 dark:text-gray-400">字段</span>
          </div>
        )}
        {(dd.indexes_added?.length > 0 || dd.indexes_removed?.length > 0) && (
          <div className="flex items-center gap-1 rounded-lg border bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800">
            <Hash className="h-4 w-4 text-gray-400" />
            <span className="text-green-600 font-medium">+{dd.indexes_added?.length || 0}</span>
            <span className="text-gray-300 dark:text-gray-600">/</span>
            <span className="text-red-500 font-medium">-{dd.indexes_removed?.length || 0}</span>
            <span className="text-gray-500 ml-1 dark:text-gray-400">索引</span>
          </div>
        )}
        {dd.breaking_changes && (
          <div className="flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm dark:border-red-800 dark:bg-red-950">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <span className="text-red-700 font-medium dark:text-red-300">{dd.breaking_details?.length || 0}</span>
            <span className="text-red-600 dark:text-red-400">项破坏性变更</span>
          </div>
        )}
      </div>

      {/* Diff sections */}
      <div className="space-y-3">
        <DiffSection title="新增表" icon={<span className="text-green-600 font-bold">+</span>} count={dd.tables_added?.length || 0}>
          {dd.tables_added?.map((t: any, i: number) => (
            <AddedItem key={i} name={t.name} columns={t.columns} />
          ))}
        </DiffSection>

        <DiffSection title="删除表" icon={<span className="text-red-500 font-bold">−</span>} count={dd.tables_removed?.length || 0}>
          {dd.tables_removed?.map((t: any, i: number) => (
            <RemovedItem key={i} name={t.name} />
          ))}
        </DiffSection>

        <DiffSection title="重命名表" icon={<span className="text-orange-600">🔄</span>} count={dd.tables_renamed?.length || 0}>
          {dd.tables_renamed?.map((t: any, i: number) => (
            <RenamedItem key={i} oldName={t.old_name || t.before} newName={t.new_name || t.after} />
          ))}
        </DiffSection>

        <DiffSection title="新增字段" icon={<span className="text-green-600 font-bold">+</span>} count={dd.fields_added?.length || 0}>
          {dd.fields_added?.map((f: any, i: number) => (
            <AddedItem key={i} name={`${f.table}.${f.field || f.name}`} />
          ))}
        </DiffSection>

        <DiffSection title="删除字段" icon={<span className="text-red-500 font-bold">−</span>} count={dd.fields_removed?.length || 0}>
          {dd.fields_removed?.map((f: any, i: number) => (
            <RemovedItem key={i} name={`${f.table}.${f.field || f.name}`} />
          ))}
        </DiffSection>

        <DiffSection title="字段修改" icon={<span className="text-blue-600 font-bold">~</span>} count={dd.fields_modified?.length || 0} breaking>
          <div className="space-y-2">
            {dd.fields_modified?.map((f: any, i: number) => (
              <ModifiedField key={i} table={f.table} field={f.field} changes={f.changes || {}} />
            ))}
          </div>
        </DiffSection>

        <DiffSection title="新增索引" icon={<span className="text-green-600 font-bold">+</span>} count={dd.indexes_added?.length || 0}>
          {dd.indexes_added?.map((idx: any, i: number) => (
            <AddedItem key={i} name={`${idx.table || ''}.${idx.name}`} />
          ))}
        </DiffSection>

        <DiffSection title="删除索引" icon={<span className="text-red-500 font-bold">−</span>} count={dd.indexes_removed?.length || 0}>
          {dd.indexes_removed?.map((idx: any, i: number) => (
            <RemovedItem key={i} name={`${idx.table || ''}.${idx.name}`} />
          ))}
        </DiffSection>
      </div>

      {/* AI Summary */}
      <div className="rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
            <Sparkles className="h-4 w-4 text-purple-500" />
            AI 变更摘要
          </div>
          {!diff.summary && (
            <button
              onClick={() => aiSummary.mutate()}
              disabled={aiSummary.isPending}
              className="flex items-center gap-1 rounded-md bg-purple-600 px-3 py-1.5 text-xs text-white hover:bg-purple-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
            >
              {aiSummary.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
              生成摘要
            </button>
          )}
          {diff.summary && (
            <button
              onClick={() => handleCopySummary(diff.summary!)}
              className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 cursor-pointer"
            >
              {summaryCopied ? <Check className="h-3 w-3 text-green-600 dark:text-green-400" /> : <Copy className="h-3 w-3" />}
              {summaryCopied ? '已复制' : '复制'}
            </button>
          )}
        </div>
        <div className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
          {aiSummary.isPending && (
            <div className="flex items-center gap-2 text-gray-400 dark:text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              AI 正在分析变更...
            </div>
          )}
          {diff.summary && <p>{diff.summary}</p>}
          {!diff.summary && !aiSummary.isPending && (
            <p className="text-gray-400 dark:text-gray-500">点击"生成摘要"由 AI 分析本次变更</p>
          )}
        </div>
      </div>

      {/* Migration SQL */}
      <div className="rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
            <Code className="h-4 w-4 text-gray-500" />
            Migration SQL
          </div>
          {migration.data && (
            <button
              onClick={() => handleCopySql(migration.data!)}
              className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 cursor-pointer dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {sqlCopied ? <Check className="h-3 w-3 text-green-600 dark:text-green-400" /> : <Copy className="h-3 w-3" />}
              {sqlCopied ? '已复制' : '复制'}
            </button>
          )}
        </div>
        <div className="p-4">
          {!migration.data && !migration.isPending && (
            <button
              onClick={() => migration.mutate()}
              disabled={migration.isPending}
              className="flex items-center gap-1 rounded-md border px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 cursor-pointer disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {migration.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Code className="h-3 w-3" />}
              生成迁移脚本
            </button>
          )}
          {migration.isPending && (
            <div className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              生成中...
            </div>
          )}
          {migration.data && (
            <pre className="overflow-x-auto rounded-md bg-gray-900 p-4 text-xs text-green-400">
              <code>{migration.data}</code>
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}
