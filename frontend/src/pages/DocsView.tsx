import { useState } from 'react'
import { useParams, Link } from 'react-router'
import { Loader2, AlertCircle, FileText, Trash2, Sparkles, Download, Eye } from 'lucide-react'
import { useDocs, useGenerateDoc, useDeleteDoc } from '@/hooks/useDocs'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { formatDate } from '@/lib/utils'

export function DocsView() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, error } = useDocs(id!)
  const generateDoc = useGenerateDoc(id!)
  const deleteDoc = useDeleteDoc(id!)
  const [aiEnhance, setAiEnhance] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const docs = data?.items ?? []

  const handleGenerate = async () => {
    try {
      await generateDoc.mutateAsync({ ai_enhance: aiEnhance })
    } catch {
      // ignore
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteDoc.mutateAsync(deleteId)
    } finally {
      setDeleteId(null)
    }
  }

  const handleDownload = (doc: any) => {
    // Navigate to doc preview to get content, or open in new tab
    window.open(`/projects/${id}/docs/${doc.id}`, '_blank')
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={generateDoc.isPending}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
          >
            {generateDoc.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            生成文档
          </button>
          <label className="flex items-center gap-1.5 rounded-md border bg-white px-3 py-2 text-xs text-gray-600 cursor-pointer hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
            <Sparkles className="h-3.5 w-3.5 text-purple-500" />
            <span>AI 增强</span>
            <input
              type="checkbox"
              checked={aiEnhance}
              onChange={(e) => setAiEnhance(e.target.checked)}
              className="ml-1"
            />
          </label>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 py-16 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">加载失败</span>
        </div>
      )}

      {!isLoading && !error && docs.length === 0 && (
        <div className="py-16 text-center text-sm text-gray-400 dark:text-gray-500">
          尚未生成文档，点击"生成文档"按钮创建
        </div>
      )}

      {!isLoading && !error && docs.length > 0 && (
        <div className="overflow-hidden rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400">
                <th className="py-3 pl-4 pr-2 font-medium">标题</th>
                <th className="py-3 px-2 font-medium">AI</th>
                <th className="py-3 px-2 font-medium">时间</th>
                <th className="py-3 pr-4 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50">
                  <td className="py-3 pl-4 pr-2 font-medium text-gray-900 dark:text-gray-100">{doc.title}</td>
                  <td className="px-2">
                    {doc.ai_enhanced ? (
                      <Sparkles className="h-4 w-4 text-purple-500" />
                    ) : (
                      <span className="text-gray-300 dark:text-gray-600">-</span>
                    )}
                  </td>
                  <td className="px-2 text-xs text-gray-500 dark:text-gray-400">{formatDate(doc.created_at)}</td>
                  <td className="pr-4">
                    <div className="flex items-center gap-1">
                      <Link
                        to={`/projects/${id}/docs/${doc.id}`}
                        className="flex items-center gap-1 rounded px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 no-underline dark:text-blue-400 dark:hover:bg-blue-900/30"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        预览
                      </Link>
                      <button
                        onClick={() => handleDownload(doc)}
                        className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 cursor-pointer dark:text-gray-400 dark:hover:bg-gray-700"
                      >
                        <Download className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => setDeleteId(doc.id)}
                        className="flex items-center gap-1 rounded px-2 py-1 text-xs text-red-500 hover:bg-red-50 cursor-pointer dark:hover:bg-red-900/30"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteId}
        title="删除文档"
        message="确定要删除此文档吗？"
        confirmLabel="删除"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  )
}
