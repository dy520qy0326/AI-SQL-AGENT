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
    <div className="rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer dark:text-gray-200 dark:hover:bg-gray-700/50"
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        {icon}
        {title}
        <span className={`ml-1 rounded-full px-2 py-0.5 text-xs ${
          breaking ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
        }`}>
          {count}
        </span>
        {breaking && <AlertTriangle className="h-4 w-4 text-red-500" />}
      </button>
      {open && (
        <div className="border-t px-4 py-3 dark:border-gray-700">
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
      <span className="h-5 w-5 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold dark:bg-green-900/40 dark:text-green-300">+</span>
      <span className="font-medium text-gray-900 dark:text-gray-100">{name}</span>
      {columns && columns.length > 0 && (
        <span className="text-xs text-gray-400 dark:text-gray-500">({columns.length} 个字段)</span>
      )}
    </div>
  )
}

export function RemovedItem({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm">
      <span className="h-5 w-5 rounded-full bg-red-100 text-red-700 flex items-center justify-center text-xs font-bold dark:bg-red-900/40 dark:text-red-300">−</span>
      <span className="font-medium text-gray-500 line-through dark:text-gray-400">{name}</span>
    </div>
  )
}

export function RenamedItem({ oldName, newName }: { oldName: string; newName: string }) {
  return (
    <div className="flex items-center gap-2 py-1 text-sm">
      <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">🔄</span>
      <span className="text-gray-500 line-through dark:text-gray-400">{oldName}</span>
      <span className="text-gray-400 dark:text-gray-500">→</span>
      <span className="font-medium text-gray-900 dark:text-gray-100">{newName}</span>
    </div>
  )
}

export function ModifiedField({ table, field, changes }: { table: string; field: string; changes: Record<string, { before: string; after: string }> }) {
  const isBreaking = Object.keys(changes).length > 0
  return (
    <div className={`rounded-md border p-3 ${isBreaking ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950' : 'border-blue-100 bg-blue-50 dark:border-blue-800 dark:bg-blue-950'}`}>
      <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-gray-100">
        {isBreaking && <AlertTriangle className="h-4 w-4 text-red-500" />}
        {table}.{field}
      </div>
      <div className="mt-1.5 space-y-1">
        {Object.entries(changes).map(([attr, vals]) => (
          <div key={attr} className="flex items-center gap-2 text-xs">
            <span className="w-16 text-gray-500 dark:text-gray-400">{attr}</span>
            <span className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-red-700 line-through dark:bg-red-900/40 dark:text-red-300">{vals.before}</span>
            <span className="text-gray-400 dark:text-gray-500">→</span>
            <span className="rounded bg-green-100 px-1.5 py-0.5 font-mono text-green-700 dark:bg-green-900/40 dark:text-green-300">{vals.after}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export { DiffSection }
