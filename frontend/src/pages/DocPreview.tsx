import { useParams, Link } from 'react-router'
import { ArrowLeft, Loader2, AlertCircle, Copy, Check, Download } from 'lucide-react'
import { useDocContent } from '@/hooks/useDocs'
import { MarkdownViewer } from '@/components/MarkdownViewer'
import { useState } from 'react'

export function DocPreview() {
  const { id, docId } = useParams<{ id: string; docId: string }>()
  const { data: content, isLoading, error } = useDocContent(id!, docId!)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!content) return
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  const handleDownload = () => {
    if (!content) return
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `data-dictionary-${docId}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Link
          to={`/projects/${id}/docs`}
          className="inline-flex items-center gap-1 text-sm text-gray-500 no-underline hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          返回文档列表
        </Link>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-md border bg-white px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 cursor-pointer"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-green-600" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            {copied ? '已复制' : '复制'}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 rounded-md border bg-white px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 cursor-pointer"
          >
            <Download className="h-3.5 w-3.5" />
            下载
          </button>
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
          <span className="text-sm">文档加载失败</span>
        </div>
      )}

      {content && (
        <div className="rounded-lg border bg-white p-6">
          <MarkdownViewer content={content} />
        </div>
      )}
    </div>
  )
}
