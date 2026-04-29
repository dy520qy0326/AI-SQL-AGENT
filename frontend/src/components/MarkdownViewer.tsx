import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownViewerProps {
  content: string
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
  return (
    <div className="prose prose-sm max-w-none prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:bg-gray-100 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-gray-300 prose-td:px-3 prose-td:py-2 dark:prose-invert dark:prose-th:border-gray-600 dark:prose-th:bg-gray-700 dark:prose-td:border-gray-600">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}
