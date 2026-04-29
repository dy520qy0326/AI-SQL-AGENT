import type { Column } from '@/types/table'

interface ColumnTableProps {
  columns: Column[]
}

export function ColumnTable({ columns }: ColumnTableProps) {
  if (columns.length === 0) {
    return <p className="py-4 text-sm text-gray-400">无字段信息</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500">
            <th className="py-2 pr-2 font-medium">#</th>
            <th className="py-2 pr-2 font-medium">字段名</th>
            <th className="py-2 pr-2 font-medium">类型</th>
            <th className="py-2 pr-2 font-medium">NULL</th>
            <th className="py-2 pr-2 font-medium">PK</th>
            <th className="py-2 pr-2 font-medium">默认值</th>
            <th className="py-2 font-medium">注释</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((col) => (
            <tr key={col.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="py-2 pr-2 text-gray-400">{col.ordinal_position}</td>
              <td className="py-2 pr-2 font-medium text-gray-900">{col.name}</td>
              <td className="py-2 pr-2 text-gray-600">
                {col.data_type}
                {col.length ? `(${col.length})` : ''}
              </td>
              <td className="py-2 pr-2">{col.nullable ? <span className="text-green-600">YES</span> : <span className="text-red-500">NO</span>}</td>
              <td className="py-2 pr-2">{col.is_primary_key ? <span className="text-amber-600">PK</span> : ''}</td>
              <td className="py-2 pr-2 font-mono text-xs text-gray-500">{col.default_value ?? '-'}</td>
              <td className="py-2 text-gray-500">{col.comment || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
