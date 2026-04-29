import { useState } from 'react'
import { Search, Plus, Loader2, AlertCircle } from 'lucide-react'
import { Layout } from '@/components/Layout'
import { ProjectCard } from '@/components/ProjectCard'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { useProjects, useCreateProject, useDeleteProject } from '@/hooks/useProjects'

export function ProjectList() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const size = 12
  const { data, isLoading, error } = useProjects(page, size)
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()

  const filtered = data?.items.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()),
  )

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      const project = await createProject.mutateAsync({ name: newName.trim(), description: newDesc.trim() || undefined })
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      window.location.href = `/projects/${project.id}`
    } catch {
      // error handled by react query
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteProject.mutateAsync(deleteId)
    } finally {
      setDeleteId(null)
    }
  }

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">项目列表</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          新建项目
        </button>
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="搜索项目..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-400"
        />
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center gap-2 py-20 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span>加载失败，请确认后端服务已启动</span>
        </div>
      )}

      {!isLoading && !error && filtered && filtered.length === 0 && (
        <div className="py-20 text-center text-gray-400 dark:text-gray-500">
          {search ? '没有匹配的项目' : '还没有项目，点击右上角"新建项目"开始'}
        </div>
      )}

      {!isLoading && !error && filtered && filtered.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((p) => (
              <div key={p.id} className="relative group">
                <ProjectCard project={p} />
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    setDeleteId(p.id)
                  }}
                  className="absolute top-2 right-2 rounded p-1 text-gray-300 opacity-0 transition hover:text-red-500 group-hover:opacity-100 cursor-pointer dark:text-gray-600 dark:hover:text-red-400"
                  title="删除项目"
                >
                  <span className="text-xs">✕</span>
                </button>
              </div>
            ))}
          </div>

          {data && data.total > size && (
            <div className="mt-6 flex items-center justify-center gap-2 text-sm">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border px-3 py-1 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed dark:border-gray-600 dark:text-gray-300"
              >
                上一页
              </button>
              <span className="text-gray-500 dark:text-gray-400">
                第 {page} / {Math.ceil(data.total / size)} 页（共 {data.total} 个）
              </span>
              <button
                disabled={page >= Math.ceil(data.total / size)}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border px-3 py-1 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed dark:border-gray-600 dark:text-gray-300"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}

      {/* Create Dialog */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800 dark:border dark:border-gray-700">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">新建项目</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300">项目名称 *</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="例如：电商系统"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-400"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300">描述（可选）</label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="项目描述..."
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-400"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => { setShowCreate(false); setNewName(''); setNewDesc('') }}
                className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || createProject.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
              >
                {createProject.isPending ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteId}
        title="删除项目"
        message="确定要删除此项目吗？此操作不可撤销，所有相关数据将被清除。"
        confirmLabel="删除"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </Layout>
  )
}
