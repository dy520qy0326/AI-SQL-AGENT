import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { GraphData } from '@/types/graph'

interface GraphParams {
  projectId: string
  type?: string
  minConfidence?: number
}

export function useGraph({ projectId, type, minConfidence = 0 }: GraphParams) {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  if (minConfidence > 0) params.set('min_confidence', String(minConfidence))

  const query = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['graph', projectId, { type, minConfidence }],
    queryFn: () => api.get<GraphData>(`/api/projects/${projectId}/graph${query}`),
    enabled: !!projectId,
  })
}

export function useMermaid(projectId: string, minConfidence = 0) {
  const params = new URLSearchParams()
  if (minConfidence > 0) params.set('min_confidence', String(minConfidence))
  const query = params.toString() ? `?${params.toString()}` : ''

  return useQuery({
    queryKey: ['mermaid', projectId],
    queryFn: () => api.get<string>(`/api/projects/${projectId}/mermaid${query}`),
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
