import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { TableSummary, TableDetail } from '@/types/table'

export function useTables(projectId: string) {
  return useQuery({
    queryKey: ['tables', projectId],
    queryFn: () => api.get<TableSummary[]>(`/api/projects/${projectId}/tables`),
    enabled: !!projectId,
  })
}

export function useTableDetail(projectId: string, tableId: string) {
  return useQuery({
    queryKey: ['table', projectId, tableId],
    queryFn: () => api.get<TableDetail>(`/api/projects/${projectId}/tables/${tableId}`),
    enabled: !!projectId && !!tableId,
  })
}
