export interface Session {
  id: string
  project_id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  sources?: { table: string; column?: string; description?: string }[]
  created_at: string
}

export interface AskRequest {
  question: string
  session_id?: string
}

export interface AskSyncResponse {
  answer: string
  sources?: { table: string; column?: string; description?: string }[]
  session_id: string
}

export interface SessionCreate {
  project_id: string
  title?: string
}
