export interface Project {
  id: string
  name: string
  description?: string
  dialect?: string
  table_count: number
  relation_count: number
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  dialect?: string
}

export interface UploadRequest {
  sql_content: string
}

export interface UploadResponse {
  tables_count: number
  relations_count: number
  errors: { statement_index: number; line: number; message: string }[]
}

export interface ProjectListResponse {
  items: Project[]
  total: number
  page: number
  size: number
}
