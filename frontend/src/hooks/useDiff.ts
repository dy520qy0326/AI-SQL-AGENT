import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Diff, DiffRequest, DiffListResponse } from '@/types/diff'

export function useDiffs(projectId: string) {
  return useQuery({
    queryKey: ['diffs', projectId],
    queryFn: () => api.get<DiffListResponse>(`/api/projects/${projectId}/diffs`),
    enabled: !!projectId,
  })
}

export function useDiff(projectId: string, diffId: string) {
  return useQuery({
    queryKey: ['diff', projectId, diffId],
    queryFn: () => api.get<Diff>(`/api/projects/${projectId}/diff/${diffId}`),
    enabled: !!projectId && !!diffId,
  })
}

export function useCreateDiff(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: DiffRequest) =>
      api.post<Diff>(`/api/projects/${projectId}/diff`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diffs', projectId] })
    },
  })
}

export function useDiffAiSummary(projectId: string, diffId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api.post<{ summary: string }>(`/api/projects/${projectId}/diff/${diffId}/ai-summary`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diff', projectId, diffId] })
    },
  })
}

export function useDiffMigration(projectId: string, diffId: string) {
  return useMutation({
    mutationFn: () =>
      api.get<string>(`/api/projects/${projectId}/diff/${diffId}/migration`),
  })
}
