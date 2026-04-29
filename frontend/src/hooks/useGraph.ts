import { useQuery } from '@tanstack/react-query'
import { api, ApiError } from '@/lib/api'
import type { GraphData } from '@/types/graph'

const BASE = import.meta.env.VITE_API_BASE || ''

interface GraphParams {
  projectId: string
  type?: string
  minConfidence?: number
  tableIds?: string[]
}

export function useGraph({ projectId, type, minConfidence = 0, tableIds }: GraphParams) {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  if (minConfidence > 0) params.set('min_confidence', String(minConfidence))
  if (tableIds && tableIds.length > 0) params.set('table_ids', tableIds.join(','))

  const query = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['graph', projectId, { type, minConfidence, tableIds }],
    queryFn: () => api.get<GraphData>(`/api/projects/${projectId}/graph${query}`),
    enabled: !!projectId,
  })
}

export function useMermaid(projectId: string, minConfidence = 0, tableIds?: string[]) {
  const params = new URLSearchParams()
  if (minConfidence > 0) params.set('min_confidence', String(minConfidence))
  if (tableIds && tableIds.length > 0) params.set('table_ids', tableIds.join(','))
  const query = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['mermaid', projectId, { minConfidence, tableIds }],
    queryFn: async () => {
      const res = await fetch(`${BASE}/api/projects/${projectId}/mermaid${query}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }))
        throw new ApiError(res.status, body.detail ?? JSON.stringify(body))
      }
      return res.text()
    },
    enabled: !!projectId,
  })
}

export function useRelations(projectId: string, type?: string, minConfidence = 0) {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  if (minConfidence > 0) params.set('min_confidence', String(minConfidence))
  const query = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['relations', projectId, { type, minConfidence }],
    queryFn: () => api.get<any>(`/api/projects/${projectId}/relations${query}`),
    enabled: !!projectId,
  })
}
