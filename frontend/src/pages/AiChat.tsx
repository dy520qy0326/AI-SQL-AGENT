import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router'
import { Loader2, AlertCircle, Lightbulb } from 'lucide-react'
import { useProjectSessions, useSessionMessages, useCreateSession, useDeleteSession } from '@/hooks/useSessions'
import { useAskStream } from '@/hooks/useAsk'
import { ChatMessage } from '@/components/ChatMessage'
import { ChatInput } from '@/components/ChatInput'
import { SessionList } from '@/components/SessionList'
import type { Message } from '@/types/session'

const SUGGESTIONS = [
  '这个数据库包含哪些表？',
  '表和表之间有哪些关联关系？',
  '有哪些字段是主键？',
  '列举所有包含外键的表',
]

export function AiChat() {
  const { id } = useParams<{ id: string }>()
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [localMessages, setLocalMessages] = useState<Message[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  const { data: sessionsData, isLoading: sessionsLoading } = useProjectSessions(id!)
  const { data: messagesData, isLoading: messagesLoading } = useSessionMessages(activeSessionId)
  const createSession = useCreateSession()
  const deleteSession = useDeleteSession()
  const { ask } = useAskStream()

  const sessions = sessionsData?.items ?? []
  const savedMessages = messagesData?.items ?? []

  const displayMessages = activeSessionId ? savedMessages : localMessages

  useEffect(() => {
    setLocalMessages([])
    setStreamingContent('')
    setError(null)
  }, [activeSessionId])

  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  })

  const handleScroll = useCallback(() => {
    const el = messagesEndRef.current?.parentElement
    if (el) {
      const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
      setAutoScroll(isAtBottom)
    }
  }, [])

  const handleSend = async (question: string) => {
    setError(null)
    let sessionId = activeSessionId

    // Create session if none active
    if (!sessionId) {
      try {
        const session = await createSession.mutateAsync({
          project_id: id!,
          title: question.slice(0, 50),
        })
        sessionId = session.id
        setActiveSessionId(sessionId)
      } catch {
        setError('创建会话失败')
        return
      }
    }

    const userMsg: Message = {
      id: `local-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }

    setLocalMessages((prev) => [...prev, userMsg])
    setIsStreaming(true)
    setStreamingContent('')

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await ask(
        id!,
        { question, session_id: sessionId },
        (chunk) => {
          setStreamingContent((prev) => prev + chunk)
        },
        controller.signal,
      )
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || '请求失败')
      }
    } finally {
      setIsStreaming(false)
      setStreamingContent('')
      abortRef.current = null
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }

  const handleNewSession = () => {
    setActiveSessionId(null)
    setLocalMessages([])
    setStreamingContent('')
    setError(null)
  }

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession.mutateAsync(sessionId)
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setLocalMessages([])
      }
    } catch {
      // ignore
    }
  }

  const hasConversation = displayMessages.length > 0 || isStreaming || streamingContent

  return (
    <div className="flex gap-4" style={{ height: 'calc(100vh - 220px)' }}>
      {/* Sidebar */}
      <div className="w-56 shrink-0 rounded-lg border bg-white p-3">
        <SessionList
          sessions={sessions}
          activeId={activeSessionId}
          onSelect={setActiveSessionId}
          onNew={handleNewSession}
          onDelete={handleDeleteSession}
        />
      </div>

      {/* Chat Area */}
      <div className="flex flex-1 flex-col rounded-lg border bg-white">
        {!hasConversation && !sessionsLoading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="max-w-md text-center">
              <Lightbulb className="mx-auto mb-4 h-10 w-10 text-amber-400" />
              <p className="mb-4 text-sm text-gray-500">
                输入关于数据库结构的问题，AI 将根据解析结果为你解答
              </p>
              <div className="space-y-2">
                {SUGGESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    className="block w-full rounded-md border px-3 py-2 text-left text-sm text-gray-600 hover:bg-gray-50 cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {sessionsLoading && (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          </div>
        )}

        {messagesLoading && (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          </div>
        )}

        {hasConversation && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4" onScroll={handleScroll}>
            {displayMessages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isStreaming && streamingContent && (
              <ChatMessage
                message={{ role: 'assistant', content: streamingContent, sources: [] }}
                isStreaming
              />
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {error && (
          <div className="mx-4 mb-2 flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="border-t p-3">
          <ChatInput
            onSend={handleSend}
            onStop={handleStop}
            disabled={createSession.isPending}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </div>
  )
}
