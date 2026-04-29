import type { Version } from '@/types/diff'

interface VersionSelectorProps {
  versions: Version[]
  oldVersion: string
  newVersion: string
  onOldChange: (id: string) => void
  onNewChange: (id: string) => void
  onCompare: () => void
  loading?: boolean
}

export function VersionSelector({
  versions,
  oldVersion,
  newVersion,
  onOldChange,
  onNewChange,
  onCompare,
  loading,
}: VersionSelectorProps) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4">
      <div>
        <label className="mb-1 block text-xs text-gray-500">旧版本</label>
        <select
          value={oldVersion}
          onChange={(e) => onOldChange(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
        >
          <option value="">选择版本...</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id} disabled={v.id === newVersion}>
              {v.version_tag} ({v.tables_count} 张表)
            </option>
          ))}
        </select>
      </div>
      <div className="pb-2 text-gray-400 text-lg">→</div>
      <div>
        <label className="mb-1 block text-xs text-gray-500">新版本</label>
        <select
          value={newVersion}
          onChange={(e) => onNewChange(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
        >
          <option value="">选择版本...</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id} disabled={v.id === oldVersion}>
              {v.version_tag} ({v.tables_count} 张表)
            </option>
          ))}
        </select>
      </div>
      <button
        onClick={onCompare}
        disabled={!oldVersion || !newVersion || loading}
        className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
      >
        对比差异
      </button>
    </div>
  )
}
