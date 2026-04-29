export interface GraphNode {
  id: string
  label: string
  schema_name?: string
  column_count: number
}

export interface GraphEdge {
  id: string
  from: string
  to: string
  type: string
  confidence: number
  label?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
