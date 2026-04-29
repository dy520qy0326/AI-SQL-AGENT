import { useState, useRef, useEffect } from 'react'
import { Send, Square } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  disabled?: boolean
  isStreaming?: boolean
}

export function ChatInput({ onSend, onStop, disabled, isStreaming }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isStreaming && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isStreaming])

  const handleSubmit = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (isStreaming) {
        onStop?.()
      } else {
        handleSubmit()
      }
    }
  }

  return (
    <div className="flex items-end gap-2 rounded-lg border bg-white p-3">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入关于数据库结构的问题..."
        rows={2}
        disabled={disabled}
        className="min-h-[44px] flex-1 resize-none text-sm outline-none disabled:bg-gray-50"
      />
      <button
        onClick={isStreaming ? onStop : handleSubmit}
        disabled={!isStreaming && (!value.trim() || disabled)}
        className={`flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium text-white transition cursor-pointer disabled:cursor-not-allowed ${
          isStreaming
            ? 'bg-red-500 hover:bg-red-600'
            : 'bg-blue-600 hover:bg-blue-700 disabled:opacity-40'
        }`}
      >
        {isStreaming ? (
          <Square className="h-4 w-4 fill-white" />
        ) : (
          <Send className="h-4 w-4" />
        )}
      </button>
    </div>
  )
}
