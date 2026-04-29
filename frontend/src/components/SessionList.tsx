import { MessageSquare, Plus, Trash2 } from 'lucide-react'
import type { Session } from '@/types/session'

interface SessionListProps {
  sessions: Session[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export function SessionList({ sessions, activeId, onSelect, onNew, onDelete }: SessionListProps) {
  return (
    <div className="flex h-full flex-col">
      <button
        onClick={onNew}
        className="mb-3 flex items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 cursor-pointer dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
      >
        <Plus className="h-4 w-4" />
        新对话
      </button>

      <div className="flex-1 space-y-1 overflow-y-auto">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-400 py-4 text-center dark:text-gray-500">暂无对话</p>
        )}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`group flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition ${
              activeId === session.id
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
            }`}
            onClick={() => onSelect(session.id)}
          >
            <div className="flex items-center gap-2 overflow-hidden">
              <MessageSquare className="h-4 w-4 shrink-0" />
              <span className="truncate">{session.title}</span>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(session.id)
              }}
              className="shrink-0 rounded p-1 text-gray-300 opacity-0 transition hover:text-red-500 group-hover:opacity-100 cursor-pointer dark:text-gray-600 dark:hover:text-red-400"
              title="删除会话"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
