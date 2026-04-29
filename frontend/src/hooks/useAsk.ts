import { api } from '@/lib/api'
import type { AskRequest, AskSyncResponse } from '@/types/session'
import { useMutation } from '@tanstack/react-query'

export function useAskStream() {
  return {
    ask: async (
      projectId: string,
      body: AskRequest,
      onChunk: (content: string) => void,
      signal?: AbortSignal,
    ) => {
      await api.streamSSE(
        `/api/projects/${projectId}/ask`,
        body,
        onChunk,
        signal,
      )
    },
  }
}

export function useAskSync(projectId: string) {
  return useMutation({
    mutationFn: (body: AskRequest) =>
      api.post<AskSyncResponse>(`/api/projects/${projectId}/ask/sync`, body),
  })
}
