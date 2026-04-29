import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Version, VersionCreateRequest, VersionListResponse } from '@/types/diff'

export function useVersions(projectId: string) {
  return useQuery({
    queryKey: ['versions', projectId],
    queryFn: () => api.get<VersionListResponse>(`/api/projects/${projectId}/versions`),
    enabled: !!projectId,
  })
}

export function useCreateVersion(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: VersionCreateRequest) =>
      api.post<Version>(`/api/projects/${projectId}/versions`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions', projectId] })
    },
  })
}

export function useDeleteVersion(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (versionId: string) =>
      api.del(`/api/projects/${projectId}/versions/${versionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions'] })
    },
  })
}
