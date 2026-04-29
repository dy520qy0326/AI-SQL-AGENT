import { useEffect, useRef, useState, useCallback } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'

interface MermaidDiagramProps {
  chart: string
  isDark?: boolean
  onError?: (error: Error) => void
}

type Status = 'loading' | 'ready' | 'error'

export function MermaidDiagram({ chart, isDark = false, onError }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<Status>('loading')
  const [errorMsg, setErrorMsg] = useState('')
  const idRef = useRef(0)

  const renderMermaid = useCallback(async () => {
    setStatus('loading')
    setErrorMsg('')

    try {
      const mermaid = (await import('mermaid')).default

      mermaid.initialize({
        startOnLoad: false,
        theme: isDark ? 'dark' : 'default',
        securityLevel: 'loose',
        maxTextSize: 500000,
      })

      const id = `mermaid-${++idRef.current}`
      const { svg } = await mermaid.render(id, chart)

      if (containerRef.current) {
        containerRef.current.innerHTML = svg
      }
      setStatus('ready')
    } catch (err) {
      const msg = err instanceof Error ? err.message : '渲染失败'
      setErrorMsg(msg)
      setStatus('error')
      onError?.(err instanceof Error ? err : new Error(msg))
    }
  }, [chart, isDark, onError])

  useEffect(() => {
    renderMermaid()
  }, [renderMermaid])

  return (
    <div className="relative h-[600px] overflow-auto rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
      <div
        ref={containerRef}
        className="mermaid-wrapper flex min-h-full items-start justify-center p-4"
      />

      {status === 'loading' && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {status === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-white/80 dark:bg-gray-800/80">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Mermaid 渲染失败
          </span>
          <span className="max-w-md px-4 text-center text-xs text-gray-400 dark:text-gray-500">
            {errorMsg}
          </span>
        </div>
      )}
    </div>
  )
}
