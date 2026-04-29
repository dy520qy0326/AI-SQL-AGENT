export interface GraphNode {
  id: string
  name: string
  schema_name?: string
  column_count: number
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  confidence: number
  label?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
