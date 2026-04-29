import type { ForeignKey } from '@/types/table'
import { ArrowRight } from 'lucide-react'

interface ForeignKeyTableProps {
  foreignKeys: ForeignKey[]
}

export function ForeignKeyTable({ foreignKeys }: ForeignKeyTableProps) {
  if (foreignKeys.length === 0) {
    return <p className="py-3 text-sm text-gray-400">无外键约束</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500">
            <th className="py-2 pr-2 font-medium">约束名</th>
            <th className="py-2 pr-2 font-medium">来源字段</th>
            <th className="py-2 pr-2 font-medium" />
            <th className="py-2 pr-2 font-medium">引用表</th>
            <th className="py-2 font-medium">引用字段</th>
          </tr>
        </thead>
        <tbody>
          {foreignKeys.map((fk) => (
            <tr key={fk.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="py-2 pr-2 font-mono text-xs text-gray-500">{fk.constraint_name || '-'}</td>
              <td className="py-2 pr-2 text-gray-900">
                {fk.columns.map((c, i) => (
                  <span key={i} className="rounded bg-blue-50 px-1.5 py-0.5 font-mono text-xs text-blue-700">{c}</span>
                ))}
              </td>
              <td className="py-2 pr-2 text-gray-400"><ArrowRight className="h-3.5 w-3.5" /></td>
              <td className="py-2 pr-2 text-gray-900">{fk.ref_table_name}</td>
              <td className="py-2 text-gray-900">
                {fk.ref_columns.map((c, i) => (
                  <span key={i} className="rounded bg-green-50 px-1.5 py-0.5 font-mono text-xs text-green-700">{c}</span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
