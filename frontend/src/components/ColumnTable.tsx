import type { Column } from '@/types/table'

interface ColumnTableProps {
  columns: Column[]
}

export function ColumnTable({ columns }: ColumnTableProps) {
  if (columns.length === 0) {
    return <p className="py-4 text-sm text-gray-400 dark:text-gray-500">无字段信息</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
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
            <tr key={col.id} className="border-b last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50">
              <td className="py-2 pr-2 text-gray-400 dark:text-gray-500">{col.ordinal_position}</td>
              <td className="py-2 pr-2 font-medium text-gray-900 dark:text-gray-100">{col.name}</td>
              <td className="py-2 pr-2 text-gray-600 dark:text-gray-300">
                {col.data_type}
                {col.length ? `(${col.length})` : ''}
              </td>
              <td className="py-2 pr-2">{col.nullable ? <span className="text-green-600 dark:text-green-400">YES</span> : <span className="text-red-500 dark:text-red-400">NO</span>}</td>
              <td className="py-2 pr-2">{col.is_primary_key ? <span className="text-amber-600 dark:text-amber-400">PK</span> : ''}</td>
              <td className="py-2 pr-2 font-mono text-xs text-gray-500 dark:text-gray-400">{col.default_value ?? '-'}</td>
              <td className="py-2 text-gray-500 dark:text-gray-400">{col.comment || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
