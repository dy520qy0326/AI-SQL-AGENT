export interface Version {
  id: string
  project_id: string
  version_tag: string
  file_hash: string
  tables_count: number
  created_at?: string
}

export interface VersionCreateRequest {
  sql_content: string
  version_tag?: string
}

export interface VersionListResponse {
  items: Version[]
  total: number
}

export interface DiffRequest {
  old_version_id: string
  new_version_id: string
}

export interface DiffData {
  tables_added: any[]
  tables_removed: any[]
  tables_renamed: any[]
  fields_added: any[]
  fields_removed: any[]
  fields_modified: any[]
  fields_renamed: any[]
  indexes_added: any[]
  indexes_removed: any[]
  relations_added: any[]
  relations_removed: any[]
  breaking_changes: boolean
  breaking_details: string[]
  summary_stats: Record<string, any>
}

export interface Diff {
  id: string
  project_id: string
  old_version_id: string
  new_version_id: string
  diff_data: DiffData
  summary?: string
  breaking_changes: boolean
  created_at?: string
}

export interface DiffListResponse {
  items: Diff[]
  total: number
}
