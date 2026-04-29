import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react'

interface DiffSectionProps {
  title: string
  icon: React.ReactNode
  count: number
  breaking?: boolean
  children: React.ReactNode
}

function DiffSection({ title, icon, count, breaking, children }: DiffSectionProps) {
  const [open, setOpen] = useState(true)

  if (count === 0) return null

  return (
    <div className="rounded-lg border bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer"
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        {icon}
        {title}
        <span className={`ml-1 rounded-full px-2 py-0.5 text-xs ${
          breaking ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {count}
        </span>
        {breaking && <AlertTriangle className="h-4 w-4 text-red-500" />}
      </button>
      {open && (
        <div className="border-t px-4 py-3">
          {children}
        </div>
      )}
    </div>
  )
}

// Diff List item renderers

export function AddedItem({ name, columns }: { name: string; columns?: { name: string }[] }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm">
      <span className="h-5 w-5 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">+</span>
      <span className="font-medium text-gray-900">{name}</span>
      {columns && columns.length > 0 && (
        <span className="text-xs text-gray-400">({columns.length} 个字段)</span>
      )}
    </div>
  )
}

export function RemovedItem({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm">
      <span className="h-5 w-5 rounded-full bg-red-100 text-red-700 flex items-center justify-center text-xs font-bold">−</span>
      <span className="font-medium text-gray-500 line-through">{name}</span>
    </div>
  )
}

export function RenamedItem({ oldName, newName }: { oldName: string; newName: string }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm">
      <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs text-orange-700">🔄</span>
      <span className="text-gray-500 line-through">{oldName}</span>
      <span className="text-gray-400">→</span>
      <span className="font-medium text-gray-900">{newName}</span>
    </div>
  )
}

export function ModifiedField({ table, field, changes }: { table: string; field: string; changes: Record<string, { before: string; after: string }> }) {
  const isBreaking = Object.keys(changes).length > 0
  return (
    <div className={`rounded-md border p-3 ${isBreaking ? 'border-red-200 bg-red-50' : 'border-blue-100 bg-blue-50'}`}>
      <div className="flex items-center gap-2 text-sm font-medium text-gray-900">
        {isBreaking && <AlertTriangle className="h-4 w-4 text-red-500" />}
        {table}.{field}
      </div>
      <div className="mt-1.5 space-y-1">
        {Object.entries(changes).map(([attr, vals]) => (
          <div key={attr} className="flex items-center gap-2 text-xs">
            <span className="w-16 text-gray-500">{attr}</span>
            <span className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-red-700 line-through">{vals.before}</span>
            <span className="text-gray-400">→</span>
            <span className="rounded bg-green-100 px-1.5 py-0.5 font-mono text-green-700">{vals.after}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export { DiffSection }
