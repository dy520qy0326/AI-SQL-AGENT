import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { QueryRelationResponse, SaveRelationResponse } from '@/types/relation'

export function useQueryRelations(projectId: string) {
  const queryClient = useQueryClient()

  const preview = useMutation({
    mutationFn: (sql: string) =>
      api.post<QueryRelationResponse>(`/api/projects/${projectId}/query-relations`, { sql }),
  })

  const save = useMutation({
    mutationFn: ({ sql, relation_ids }: { sql: string; relation_ids: string[] }) =>
      api.post<SaveRelationResponse>(`/api/projects/${projectId}/query-relations/save`, {
        sql,
        relation_ids,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['graph', projectId] })
      queryClient.invalidateQueries({ queryKey: ['relations', projectId] })
    },
  })

  return { preview, save }
}
