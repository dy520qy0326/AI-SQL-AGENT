import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { UploadResponse } from '@/types/project'

export function useUploadSql(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sqlContent: string) =>
      api.post<UploadResponse>(`/api/projects/${projectId}/upload`, { sql_content: sqlContent }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['tables', projectId] })
      queryClient.invalidateQueries({ queryKey: ['graph', projectId] })
    },
  })
}
