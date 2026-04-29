import { useState, useRef, useCallback } from 'react'
import { Upload, FileText, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { EditorView, basicSetup } from 'codemirror'
import { EditorState } from '@codemirror/state'
import { sql, PostgreSQL } from '@codemirror/lang-sql'
import { useUploadSql } from '@/hooks/useUpload'
import type { UploadResponse } from '@/types/project'

interface SqlUploaderProps {
  projectId: string
  onSuccess?: (result: UploadResponse) => void
  defaultDialect?: string
}

export function SqlUploader({ projectId, onSuccess, defaultDialect }: SqlUploaderProps) {
  const [mode, setMode] = useState<'file' | 'editor'>('file')
  const [sqlContent, setSqlContent] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const editorRef = useRef<HTMLDivElement>(null)
  const editorViewRef = useRef<EditorView | null>(null)
  const uploadMutation = useUploadSql(projectId)

  // Initialize CodeMirror
  const editorInitialized = useRef(false)
  const initEditor = useCallback(() => {
    if (editorRef.current && !editorInitialized.current) {
      editorInitialized.current = true
      const isPostgres = defaultDialect?.toLowerCase() === 'postgresql'
      const lang = isPostgres ? () => sql({ dialect: PostgreSQL }) : sql

      const view = new EditorView({
        state: EditorState.create({
          doc: sqlContent,
          extensions: [
            basicSetup,
            lang(),
            EditorView.updateListener.of((update) => {
              setSqlContent(update.state.doc.toString())
            }),
          ],
        }),
        parent: editorRef.current,
      })
      editorViewRef.current = view
    }
  }, [defaultDialect, sqlContent])

  const handleFileDrop = useCallback(async (file: File) => {
    if (!file.name.endsWith('.sql')) {
      alert('请上传 .sql 文件')
      return
    }
    const text = await file.text()
    setSqlContent(text)
    uploadMutation.mutate(text, {
      onSuccess: (result) => {
        if (result.errors && result.errors.length > 0 && result.tables_count === 0) {
          return // error handled below
        }
        onSuccess?.(result)
      },
    })
  }, [uploadMutation, onSuccess])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }
  const handleDragLeave = () => setDragOver(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileDrop(file)
  }

  const handleEditorSubmit = () => {
    if (!sqlContent.trim()) return
    uploadMutation.mutate(sqlContent, {
      onSuccess: (result) => {
        if (result.errors && result.errors.length > 0 && result.tables_count === 0) {
          return
        }
        onSuccess?.(result)
      },
    })
  }

  return (
    <div className="space-y-4">
      {/* Mode Tabs */}
      <div className="flex gap-1 border-b">
        <button
          onClick={() => setMode('file')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition cursor-pointer ${
            mode === 'file'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Upload className="inline h-4 w-4 mr-1" />
          文件上传
        </button>
        <button
          onClick={() => { setMode('editor'); setTimeout(initEditor, 50) }}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition cursor-pointer ${
            mode === 'editor'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="inline h-4 w-4 mr-1" />
          SQL 编辑器
        </button>
      </div>

      {/* File Upload Mode */}
      {mode === 'file' && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => {
            const input = document.createElement('input')
            input.type = 'file'
            input.accept = '.sql'
            input.onchange = async () => {
              const file = input.files?.[0]
              if (file) handleFileDrop(file)
            }
            input.click()
          }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition ${
            dragOver
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 bg-gray-50 hover:border-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:hover:border-gray-500'
          }`}
        >
          <Upload className={`mb-3 h-10 w-10 ${dragOver ? 'text-blue-500' : 'text-gray-400'}`} />
          <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
            {dragOver ? '松开以上传' : '拖拽 .sql 文件到此处，或点击选择'}
          </p>
          <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">支持 MySQL / PostgreSQL DDL 文件</p>
        </div>
      )}

      {/* Editor Mode */}
      {mode === 'editor' && (
        <div>
          <div ref={editorRef} className="overflow-hidden rounded-lg border dark:border-gray-600" />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {defaultDialect || 'MySQL'} 语法高亮 · Ctrl+Enter 提交
            </span>
            <button
              onClick={handleEditorSubmit}
              disabled={!sqlContent.trim() || uploadMutation.isPending}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              解析 SQL
            </button>
          </div>
        </div>
      )}

      {/* Upload Result */}
      {uploadMutation.isPending && (
        <div className="flex items-center gap-2 rounded-lg border bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          正在解析 SQL...
        </div>
      )}

      {uploadMutation.isError && (
        <div className="flex items-start gap-2 rounded-lg border bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{uploadMutation.error instanceof Error ? uploadMutation.error.message : '解析失败'}</span>
        </div>
      )}

      {uploadMutation.data && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 rounded-lg border bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
            <CheckCircle className="h-4 w-4" />
            解析完成：{uploadMutation.data.tables_count} 张表，{uploadMutation.data.relations_count} 个关系
          </div>

          {uploadMutation.data.errors && uploadMutation.data.errors.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800 dark:bg-amber-950">
              <p className="mb-2 text-sm font-medium text-amber-800 dark:text-amber-200">
                解析警告（{uploadMutation.data.errors.length} 条）
              </p>
              <ul className="space-y-1">
                {uploadMutation.data.errors.map((err, i) => (
                  <li key={i} className="text-xs text-amber-700 dark:text-amber-300">
                    语句 {err.statement_index}（行 {err.line}）：{err.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
