export interface TableSummary {
  id: string
  name: string
  schema_name?: string
  comment?: string
  column_count: number
  created_at: string
}

export interface Column {
  id: string
  name: string
  data_type: string
  length?: number
  nullable: boolean
  default_value?: string
  is_primary_key: boolean
  ordinal_position: number
  comment?: string
}

export interface Index {
  id: string
  name: string
  unique: boolean
  columns: string[]
}

export interface ForeignKey {
  id: string
  columns: string[]
  ref_table_name: string
  ref_columns: string[]
  constraint_name?: string
}

export interface TableDetail extends TableSummary {
  columns: Column[]
  indexes: Index[]
  foreign_keys: ForeignKey[]
}
