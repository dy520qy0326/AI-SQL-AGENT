export interface Relation {
  id: string
  source_table_id: string
  source_table_name: string
  source_columns: string[]
  target_table_id: string
  target_table_name: string
  target_columns: string[]
  relation_type: 'FOREIGN_KEY' | 'INFERRED' | 'AI_SUGGESTED' | 'QUERY_INFERRED'
  confidence: number
  source: string
}

export interface RelationListResponse {
  items: Relation[]
  total: number
}

export interface QueryRelationPreview {
  temp_id: string
  source_table: string
  source_columns: string[]
  target_table: string
  target_columns: string[]
  join_type: string
  confidence: number
  already_exists: boolean
}

export interface QueryRelationResponse {
  dialect: string
  queries_parsed: number
  relations: QueryRelationPreview[]
  unmatched_tables: string[]
}

export interface SaveRelationItem {
  id: string
  source_table: string
  source_columns: string[]
  target_table: string
  target_columns: string[]
  relation_type: string
  confidence: number
}

export interface SaveRelationResponse {
  saved: number
  skipped: number
  relations: SaveRelationItem[]
}
