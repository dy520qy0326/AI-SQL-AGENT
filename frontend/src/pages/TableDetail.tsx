import { useParams, Link } from 'react-router'
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react'
import { useTableDetail } from '@/hooks/useTables'
import { ColumnTable } from '@/components/ColumnTable'
import { IndexTable } from '@/components/IndexTable'
import { ForeignKeyTable } from '@/components/ForeignKeyTable'

export function TableDetail() {
  const { id, tableId } = useParams<{ id: string; tableId: string }>()
  const { data: table, isLoading, error } = useTableDetail(id!, tableId!)

  return (
    <div>
      <Link
        to={`/projects/${id}/tables`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 no-underline hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <ArrowLeft className="h-4 w-4" />
        返回表列表
      </Link>

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

      {table && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">{table.name}</h2>
            {table.comment && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{table.comment}</p>}
            {table.schema_name && (
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Schema: {table.schema_name}</p>
            )}
          </div>

          <section>
            <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">字段</h3>
            <div className="rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
              <ColumnTable columns={table.columns} />
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">索引</h3>
            <div className="rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
              <IndexTable indexes={table.indexes} />
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">外键</h3>
            <div className="rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
              <ForeignKeyTable foreignKeys={table.foreign_keys} />
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
