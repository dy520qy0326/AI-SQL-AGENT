export interface Doc {
  id: string
  project_id: string
  doc_type: string
  title: string
  ai_enhanced: boolean
  created_at: string
  content_snippet?: string
}

export interface DocGenerateRequest {
  title?: string
  ai_enhance?: boolean
}

export interface DocListResponse {
  items: Doc[]
  total: number
}
