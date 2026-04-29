import { useState, useCallback, useEffect } from 'react'
import { useParams } from 'react-router'
import { Loader2, AlertCircle, Copy, Check, GitBranch, Table } from 'lucide-react'
import { useGraph, useMermaid } from '@/hooks/useGraph'
import { ErGraph } from '@/components/ErGraph'
import { MermaidDiagram } from '@/components/MermaidDiagram'
import { RelationFilters } from '@/components/RelationFilters'
import { TableSelect } from '@/components/TableSelect'
import { GraphLegend } from '@/components/GraphLegend'
import { useTheme } from '@/hooks/useTheme'
import type { GraphNode } from '@/types/graph'

type ViewMode = 'graph' | 'mermaid'

export function GraphView() {
  const { id } = useParams<{ id: string }>()
  const [type, setType] = useState('')
  const [minConfidence, setMinConfidence] = useState(0)
  const [tableIds, setTableIds] = useState<string[]>([])
  const [viewMode, setViewMode] = useState<ViewMode>('graph')
  const [copied, setCopied] = useState(false)
  const { resolved } = useTheme()
  const isDark = resolved === 'dark'

  // Reset table selection when project changes
  useEffect(() => { setTableIds([]) }, [id])

  const { data: graphData, isLoading, error } = useGraph({
    projectId: id!,
    type: type || undefined,
    minConfidence,
    tableIds: tableIds.length > 0 ? tableIds : undefined,
  })

  const handleNodeClick = useCallback((node: GraphNode) => {
    window.open(`/projects/${id}/tables/${node.id}`, '_self')
  }, [id])

  const mermaidQuery = useMermaid(id!, minConfidence, tableIds.length > 0 ? tableIds : undefined)

  const handleCopyMermaid = async () => {
    if (!mermaidQuery.data) return
    try {
      await navigator.clipboard.writeText(mermaidQuery.data)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard API may fail
    }
  }

  const hasData = graphData && graphData.nodes.length > 0

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <RelationFilters
          type={type}
          onTypeChange={setType}
          minConfidence={minConfidence}
          onConfidenceChange={setMinConfidence}
        />
        <TableSelect
          projectId={id!}
          value={tableIds}
          onChange={setTableIds}
        />
        <div className="flex items-center gap-3">
          <div className="flex overflow-hidden rounded-md border dark:border-gray-600">
            <button
              onClick={() => setViewMode('graph')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs cursor-pointer transition-colors ${
                viewMode === 'graph'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <GitBranch className="h-3.5 w-3.5" />
              关系图
            </button>
            <button
              onClick={() => setViewMode('mermaid')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs cursor-pointer transition-colors ${
                viewMode === 'mermaid'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <Table className="h-3.5 w-3.5" />
              ER 图
            </button>
          </div>
          <GraphLegend />
          <button
            onClick={handleCopyMermaid}
            disabled={!mermaidQuery.data}
            className="flex items-center gap-1.5 rounded-md border bg-white px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            复制 Mermaid
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 py-20 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">关系图加载失败</span>
        </div>
      )}

      {!isLoading && !error && viewMode === 'graph' && hasData && (
        <ErGraph data={graphData!} onNodeClick={handleNodeClick} />
      )}

      {!isLoading && !error && viewMode === 'mermaid' && mermaidQuery.data && (
        <MermaidDiagram chart={mermaidQuery.data} isDark={isDark} />
      )}

      {!isLoading && !error && viewMode === 'mermaid' && mermaidQuery.isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {!isLoading && !error && viewMode === 'mermaid' && mermaidQuery.isError && (
        <div className="flex items-center gap-2 py-20 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">Mermaid 信息加载失败</span>
        </div>
      )}

      {!isLoading && !error && !hasData && viewMode === 'graph' && (
        <div className="flex items-center justify-center py-20 text-sm text-gray-400 dark:text-gray-500">
          {type || minConfidence > 0 ? '没有匹配的关系' : '尚未解析出表关系，请先上传 SQL 文件'}
        </div>
      )}
    </div>
  )
}
