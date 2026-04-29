import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Doc, DocGenerateRequest, DocListResponse } from '@/types/doc'

export function useDocs(projectId: string) {
  return useQuery({
    queryKey: ['docs', projectId],
    queryFn: () => api.get<DocListResponse>(`/api/projects/${projectId}/docs`),
    enabled: !!projectId,
  })
}

export function useDocContent(projectId: string, docId: string) {
  return useQuery({
    queryKey: ['doc', projectId, docId],
    queryFn: () => api.get<string>(`/api/projects/${projectId}/docs/${docId}`),
    enabled: !!projectId && !!docId,
  })
}

export function useGenerateDoc(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: DocGenerateRequest) =>
      api.post<Doc>(`/api/projects/${projectId}/docs`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docs', projectId] })
    },
  })
}

export function useDeleteDoc(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (docId: string) => api.del(`/api/projects/${projectId}/docs/${docId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docs'] })
    },
  })
}
