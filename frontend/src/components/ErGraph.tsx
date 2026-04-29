import { useMemo, useCallback, useRef } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphData, GraphNode } from '@/types/graph'
import { useTheme } from '@/hooks/useTheme'

interface ErGraphProps {
  data: GraphData
  onNodeClick?: (node: GraphNode) => void
}

const EDGE_STYLES: Record<string, { color: string; lineWidth: number }> = {
  FOREIGN_KEY: { color: '#3b82f6', lineWidth: 2 },
  INFERRED: { color: '#f59e0b', lineWidth: 1.5 },
  AI_SUGGESTED: { color: '#8b5cf6', lineWidth: 1.5 },
}

export function ErGraph({ data, onNodeClick }: ErGraphProps) {
  const graphRef = useRef<any>(null)
  const { resolved } = useTheme()
  const isDark = resolved === 'dark'

  const graphData = useMemo(() => ({
    nodes: data.nodes.map((n) => ({
      ...n,
      id: n.name,
    })),
    links: data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type,
      confidence: e.confidence,
      label: e.label || e.type,
    })),
  }), [data])

  const handleNodeClick = useCallback((node: any) => {
    onNodeClick?.(node as unknown as GraphNode)
  }, [onNodeClick])

  const handleNodeHover = useCallback((node: any | null) => {
    if (!graphRef.current) return

    const highlightNodes = new Set<string>()
    const highlightLinks = new Set<string>()

    if (node) {
      highlightNodes.add(node.id)
      graphData.links.forEach((link) => {
        const sId = typeof link.source === 'object' ? (link.source as any).id : link.source
        const tId = typeof link.target === 'object' ? (link.target as any).id : link.target
        if (sId === node.id || tId === node.id) {
          highlightLinks.add(`${sId}→${tId}`)
          highlightNodes.add(sId)
          highlightNodes.add(tId)
        }
      })
    }

    const dimColor = isDark ? '#374151' : '#e5e7eb'

    graphRef.current.nodeColor((n: any) =>
      !node || highlightNodes.has(n.id) ? (n.color || '#6b7280') : dimColor
    )
    graphRef.current.linkColor((l: any) =>
      !node || highlightLinks.has(`${l.source.id}→${l.target.id}`)
        ? (EDGE_STYLES[l.type]?.color || '#9ca3af')
        : dimColor
    )
    graphRef.current.linkWidth((l: any) =>
      !node || highlightLinks.has(`${l.source.id}→${l.target.id}`)
        ? (EDGE_STYLES[l.type]?.lineWidth || 1)
        : 0.3
    )
  }, [graphData, isDark])

  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const start = link.source
    const end = link.target
    if (!start || !end || !start.x || !end.y) return

    const color = EDGE_STYLES[link.type as string]?.color || '#9ca3af'

    ctx.beginPath()
    ctx.moveTo(start.x, start.y)
    ctx.lineTo(end.x, end.y)
    ctx.strokeStyle = color
    ctx.lineWidth = EDGE_STYLES[link.type as string]?.lineWidth || 1
    ctx.stroke()
  }, [])

  const nodeLabelColor = isDark ? '#d1d5db' : '#374151'
  const particleColor = isDark ? '#9ca3af' : '#6b7280'

  return (
    <div className="h-[600px] w-full overflow-hidden rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeLabel="name"
        nodeAutoColorBy="schema_name"
        backgroundColor={isDark ? '#1f2937' : '#ffffff'}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const size = 8 + (node.column_count || 1) * 2
          const label = node.name
          const fontSize = 12 / globalScale

          ctx.beginPath()
          ctx.arc(node.x, node.y, Math.min(size, 20), 0, 2 * Math.PI)
          ctx.fillStyle = node.color || '#6b7280'
          ctx.fill()

          ctx.font = `${fontSize}px Sans-Serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillStyle = nodeLabelColor
          ctx.fillText(label, node.x, node.y + Math.min(size, 20) + 4 / globalScale)
        }}
        linkCanvasObject={paintLink}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        cooldownTicks={100}
        linkDirectionalParticles={1}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleColor={() => particleColor}
        d3VelocityDecay={0.3}
      />
    </div>
  )
}
