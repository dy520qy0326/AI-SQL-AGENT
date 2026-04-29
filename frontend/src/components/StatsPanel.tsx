import { Table2, GitCompare, BrainCircuit } from 'lucide-react'

interface StatsPanelProps {
  tableCount: number
  relationCount: number
}

export function StatsPanel({ tableCount, relationCount }: StatsPanelProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-blue-600">
          <Table2 className="h-5 w-5" />
          <span className="text-sm font-medium">数据表</span>
        </div>
        <p className="mt-2 text-2xl font-bold text-gray-900">{tableCount}</p>
      </div>
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-amber-600">
          <GitCompare className="h-5 w-5" />
          <span className="text-sm font-medium">关联关系</span>
        </div>
        <p className="mt-2 text-2xl font-bold text-gray-900">{relationCount}</p>
      </div>
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-purple-600">
          <BrainCircuit className="h-5 w-5" />
          <span className="text-sm font-medium">AI 就绪</span>
        </div>
        <p className="mt-2 text-2xl font-bold text-gray-900">●</p>
      </div>
    </div>
  )
}
