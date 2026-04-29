interface RelationFiltersProps {
  type: string
  onTypeChange: (type: string) => void
  minConfidence: number
  onConfidenceChange: (val: number) => void
}

export function RelationFilters({ type, onTypeChange, minConfidence, onConfidenceChange }: RelationFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500">关系类型</label>
        <select
          value={type}
          onChange={(e) => onTypeChange(e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-xs outline-none focus:border-blue-500"
        >
          <option value="">全部</option>
          <option value="FOREIGN_KEY">外键</option>
          <option value="INFERRED">推断</option>
          <option value="AI_SUGGESTED">AI 建议</option>
        </select>
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500">置信度 ≥ {minConfidence}</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={minConfidence}
          onChange={(e) => onConfidenceChange(Number(e.target.value))}
          className="w-24"
        />
      </div>
    </div>
  )
}
