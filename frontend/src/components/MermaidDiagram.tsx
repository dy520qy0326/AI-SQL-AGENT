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
        er: {
          layoutDirection: 'LR',
        },
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

  // Scale SVG to fit container when rendered
  useEffect(() => {
    if (status !== 'ready' || !containerRef.current) return

    const svg = containerRef.current.querySelector('svg')
    if (!svg) return

    const viewBox = svg.getAttribute('viewBox')
    if (!viewBox) return

    const parts = viewBox.split(' ').map(Number)
    if (parts.length < 4) return
    const [, , vbW, vbH] = parts
    if (!vbW || !vbH) return

    const fit = () => {
      const el = containerRef.current
      if (!el) return
      // account for padding (p-4 = 16px each side)
      const maxW = el.clientWidth - 32
      const maxH = el.clientHeight - 32

      if (maxW <= 0 || maxH <= 0) return

      const sx = maxW / vbW
      const sy = maxH / vbH
      // Never scale below 0.4x — tall diagrams scroll instead of shrinking illegibly
      const scale = Math.max(Math.min(sx, sy, 1), 0.4)

      svg.style.width = `${vbW}px`
      svg.style.height = `${vbH}px`
      svg.style.maxWidth = 'none'
      svg.style.maxHeight = 'none'
      svg.style.transformOrigin = 'top left'
      svg.style.transform = scale < 1 ? `scale(${scale})` : ''
    }

    fit()

    const observer = new ResizeObserver(fit)
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [status])

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
