import type { Index } from '@/types/table'

interface IndexTableProps {
  indexes: Index[]
}

export function IndexTable({ indexes }: IndexTableProps) {
  if (indexes.length === 0) {
    return <p className="py-3 text-sm text-gray-400 dark:text-gray-500">无索引</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <th className="py-2 pr-2 font-medium">索引名</th>
            <th className="py-2 pr-2 font-medium">类型</th>
            <th className="py-2 font-medium">字段</th>
          </tr>
        </thead>
        <tbody>
          {indexes.map((idx) => (
            <tr key={idx.id} className="border-b last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50">
              <td className="py-2 pr-2 font-mono text-xs text-gray-900 dark:text-gray-100">{idx.name}</td>
              <td className="py-2 pr-2">
                {idx.unique ? (
                  <span className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">UNIQUE</span>
                ) : (
                  <span className="text-gray-500 dark:text-gray-400">普通</span>
                )}
              </td>
              <td className="py-2 text-gray-600 dark:text-gray-300">
                <div className="flex flex-wrap gap-1">
                  {idx.columns.map((col, i) => (
                    <span key={i} className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-700 dark:text-gray-300">
                      {col}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
