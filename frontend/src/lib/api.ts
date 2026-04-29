const BASE = import.meta.env.VITE_API_BASE || ''

export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, body.detail ?? JSON.stringify(body))
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path)
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    })
  },

  del(path: string): Promise<void> {
    return request<void>(path, { method: 'DELETE' })
  },

  async streamSSE(
    path: string,
    body: unknown,
    onChunk: (content: string) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: res.statusText }))
      throw new ApiError(res.status, errBody.detail ?? JSON.stringify(errBody))
    }

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'chunk') onChunk(data.content)
          if (data.type === 'done') return
          if (data.type === 'error') throw new Error(data.message)
        }
      }
    }
  },
}
