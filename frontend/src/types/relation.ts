export interface Relation {
  id: string
  source_table_id: string
  source_table_name: string
  source_columns: string[]
  target_table_id: string
  target_table_name: string
  target_columns: string[]
  relation_type: 'FOREIGN_KEY' | 'INFERRED' | 'AI_SUGGESTED'
  confidence: number
  source: string
}

export interface RelationListResponse {
  items: Relation[]
  total: number
}
