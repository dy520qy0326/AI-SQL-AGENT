import { Bot, User } from 'lucide-react'
import type { Message } from '@/types/session'

interface ChatMessageProps {
  message: Pick<Message, 'role' | 'content' | 'sources'>
  isStreaming?: boolean
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900/40">
          <Bot className="h-4 w-4 text-purple-600 dark:text-purple-300" />
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? 'order-1' : ''}`}>
        <div
          className={`rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'border bg-white text-gray-800 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200'
          }`}
        >
          {message.content}
          {isStreaming && (
            <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-gray-400 dark:bg-gray-500" />
          )}
        </div>
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1.5 px-1">
            {message.sources.map((s, i) => (
              <span key={i} className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                {s.table}{s.column ? `.${s.column}` : ''}
              </span>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/40">
          <User className="h-4 w-4 text-blue-600 dark:text-blue-300" />
        </div>
      )}
    </div>
  )
}
