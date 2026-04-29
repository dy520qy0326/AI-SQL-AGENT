export function GraphLegend() {
  return (
    <div className="rounded-lg border bg-white p-3 text-xs text-gray-600 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
      <p className="mb-1.5 font-medium text-gray-700 dark:text-gray-300">图例</p>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-6 bg-blue-500" />
          <span>外键</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-6 border-0 border-t border-dashed border-amber-400" style={{ borderTopWidth: 2 }} />
          <span>推断关系</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block h-0.5 w-6 border-0 border-t border-dotted border-violet-400" style={{ borderTopWidth: 2 }} />
          <span>AI 建议</span>
        </div>
      </div>
    </div>
  )
}
