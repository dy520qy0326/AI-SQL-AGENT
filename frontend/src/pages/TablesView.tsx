import { useState } from 'react'
import { useParams, Link } from 'react-router'
import { Search, Loader2, AlertCircle, ChevronRight } from 'lucide-react'
import { useTables } from '@/hooks/useTables'

export function TablesView() {
  const { id } = useParams<{ id: string }>()
  const { data: tables, isLoading, error } = useTables(id!)
  const [search, setSearch] = useState('')

  const filtered = tables?.filter(
    (t) => t.name.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div>
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="搜索表名..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 py-16 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">加载失败</span>
        </div>
      )}

      {!isLoading && !error && filtered && filtered.length === 0 && (
        <div className="py-16 text-center text-sm text-gray-400">
          {search ? '没有匹配的表' : '尚未上传 SQL 文件'}
        </div>
      )}

      {!isLoading && !error && filtered && filtered.length > 0 && (
        <div className="overflow-hidden rounded-lg border bg-white">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500">
                <th className="py-3 pl-4 pr-2 font-medium">表名</th>
                <th className="py-3 px-2 font-medium">字段数</th>
                <th className="py-3 pr-4 font-medium">注释</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((table) => (
                <tr key={table.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-3 pl-4 pr-2">
                    <Link
                      to={`/projects/${id}/tables/${table.id}`}
                      className="flex items-center gap-1 font-medium text-blue-700 no-underline hover:text-blue-900"
                    >
                      {table.name}
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </td>
                  <td className="px-2 text-gray-600">{table.column_count}</td>
                  <td className="pr-4 text-gray-500">{table.comment || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
