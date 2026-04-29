import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Session, Message, SessionCreate } from '@/types/session'

interface SessionListResponse {
  items: Session[]
  total: number
}

interface MessageListResponse {
  items: Message[]
  total: number
}

export function useProjectSessions(projectId: string) {
  return useQuery({
    queryKey: ['sessions', projectId],
    queryFn: () => api.get<SessionListResponse>(`/api/projects/${projectId}/sessions`),
    enabled: !!projectId,
  })
}

export function useSessionMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () => api.get<MessageListResponse>(`/api/sessions/${sessionId}/messages`),
    enabled: !!sessionId,
  })
}

export function useCreateSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SessionCreate) => api.post<Session>('/api/sessions', data),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['sessions', session.project_id] })
    },
  })
}

export function useDeleteSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) => api.del(`/api/sessions/${sessionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}
