import { useState, useRef, useEffect, useCallback } from 'react'
import { useTables } from '@/hooks/useTables'
import { Check, ChevronDown, Search, X } from 'lucide-react'

interface TableSelectProps {
  projectId: string
  value: string[]
  onChange: (ids: string[]) => void
}

export function TableSelect({ projectId, value, onChange }: TableSelectProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { data: tables, isLoading } = useTables(projectId)

  const filtered = (tables ?? []).filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()),
  )

  const toggle = useCallback(
    (id: string) => {
      onChange(
        value.includes(id) ? value.filter((v) => v !== id) : [...value, id],
      )
    },
    [value, onChange],
  )

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Focus search input when opening
  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const totalCount = tables?.length ?? 0
  const selectedCount = value.length

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-md border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700"
      >
        <span>
          {selectedCount > 0
            ? `已选 ${selectedCount}/${totalCount} 个表`
            : '选择表'}
        </span>
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-72 rounded-md border border-gray-300 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800">
          {/* Search */}
          <div className="flex items-center gap-1 border-b border-gray-200 px-2 dark:border-gray-700">
            <Search className="h-3.5 w-3.5 shrink-0 text-gray-400" />
            <input
              ref={inputRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索表名..."
              className="min-w-0 flex-1 bg-transparent px-1 py-2 text-xs outline-none dark:text-gray-100"
            />
            {search && (
              <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600">
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Selected count + clear */}
          {selectedCount > 0 && (
            <div className="flex items-center justify-between border-b border-gray-200 px-3 py-1.5 dark:border-gray-700">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                已选 {selectedCount} 个
              </span>
              <button
                onClick={() => onChange([])}
                className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400"
              >
                清空
              </button>
            </div>
          )}

          {/* Table list */}
          <div className="max-h-64 overflow-y-auto">
            {isLoading && (
              <div className="px-3 py-4 text-center text-xs text-gray-400">加载中...</div>
            )}
            {!isLoading && filtered.length === 0 && (
              <div className="px-3 py-4 text-center text-xs text-gray-400">
                {search ? '没有匹配的表' : '暂无表数据'}
              </div>
            )}
            {!isLoading &&
              filtered.map((t) => {
                const selected = value.includes(t.id)
                return (
                  <label
                    key={t.id}
                    className="flex cursor-pointer items-center gap-2 px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <span
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                        selected
                          ? 'border-blue-600 bg-blue-600 text-white'
                          : 'border-gray-300 dark:border-gray-500'
                      }`}
                    >
                      {selected && <Check className="h-3 w-3" />}
                    </span>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggle(t.id)}
                      className="sr-only"
                    />
                    <span className="dark:text-gray-100">{t.name}</span>
                    {t.schema_name && (
                      <span className="text-gray-400 dark:text-gray-500">{t.schema_name}</span>
                    )}
                  </label>
                )
              })}
          </div>
        </div>
      )}
    </div>
  )
}
