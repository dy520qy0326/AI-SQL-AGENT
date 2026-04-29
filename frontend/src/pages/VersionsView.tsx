import { useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { Loader2, AlertCircle, Upload, Trash2 } from 'lucide-react'
import { useVersions, useCreateVersion, useDeleteVersion } from '@/hooks/useVersions'
import { useCreateDiff } from '@/hooks/useDiff'
import { VersionSelector } from '@/components/VersionSelector'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { formatDate } from '@/lib/utils'

export function VersionsView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, error } = useVersions(id!)
  const createVersion = useCreateVersion(id!)
  const deleteVersion = useDeleteVersion(id!)
  const createDiff = useCreateDiff(id!)

  const [oldVersion, setOldVersion] = useState('')
  const [newVersion, setNewVersion] = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const [sqlContent, setSqlContent] = useState('')
  const [versionTag, setVersionTag] = useState('')
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const versions = data?.items ?? []

  const handleCreateVersion = async () => {
    if (!sqlContent.trim()) return
    try {
      await createVersion.mutateAsync({
        sql_content: sqlContent,
        version_tag: versionTag.trim() || undefined,
      })
      setShowUpload(false)
      setSqlContent('')
      setVersionTag('')
    } catch {
      // handled by react query
    }
  }

  const handleCompare = async () => {
    if (!oldVersion || !newVersion) return
    try {
      const diff = await createDiff.mutateAsync({
        old_version_id: oldVersion,
        new_version_id: newVersion,
      })
      navigate(`/projects/${id}/diff/${diff.id}`)
    } catch {
      // handled by react query
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteVersion.mutateAsync(deleteId)
    } finally {
      setDeleteId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Create version button and existing diffs link */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">版本列表</h2>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 cursor-pointer"
        >
          <Upload className="h-4 w-4" />
          创建新版本
        </button>
      </div>

      {/* Version Selector for Diff */}
      {versions.length >= 2 && (
        <VersionSelector
          versions={versions}
          oldVersion={oldVersion}
          newVersion={newVersion}
          onOldChange={setOldVersion}
          onNewChange={setNewVersion}
          onCompare={handleCompare}
          loading={createDiff.isPending}
        />
      )}

      {versions.length < 2 && (
        <div className="rounded-lg border bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
          需要至少两个版本才能进行对比
        </div>
      )}

      {/* Version List */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 py-16 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">加载失败</span>
        </div>
      )}

      {!isLoading && !error && versions.length === 0 && (
        <div className="py-16 text-center text-sm text-gray-400 dark:text-gray-500">
          尚未创建版本，点击"创建新版本"上传 SQL
        </div>
      )}

      {!isLoading && !error && versions.length > 0 && (
        <div className="overflow-hidden rounded-lg border bg-white dark:border-gray-700 dark:bg-gray-800">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400">
                <th className="py-3 pl-4 pr-2 font-medium">版本标签</th>
                <th className="py-3 px-2 font-medium">表数</th>
                <th className="py-3 px-2 font-medium">文件 Hash</th>
                <th className="py-3 pr-4 font-medium">创建时间</th>
                <th className="py-3 pr-4 font-medium" />
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id} className="border-b last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50">
                  <td className="py-3 pl-4 pr-2 font-medium text-gray-900 dark:text-gray-100">{v.version_tag}</td>
                  <td className="px-2 text-gray-600 dark:text-gray-300">{v.tables_count}</td>
                  <td className="px-2 font-mono text-xs text-gray-400 dark:text-gray-500">{v.file_hash?.slice(0, 12)}...</td>
                  <td className="pr-4 text-xs text-gray-500 dark:text-gray-400">{v.created_at ? formatDate(v.created_at) : '-'}</td>
                  <td className="pr-4">
                    <button
                      onClick={() => setDeleteId(v.id)}
                      className="rounded p-1 text-gray-300 hover:text-red-500 cursor-pointer dark:text-gray-600 dark:hover:text-red-400"
                      title="删除版本"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Version Dialog */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl dark:border dark:border-gray-700 dark:bg-gray-800">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">创建新版本</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300">版本标签（可选）</label>
                <input
                  type="text"
                  value={versionTag}
                  onChange={(e) => setVersionTag(e.target.value)}
                  placeholder="例如：v2.0"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300">SQL 内容 *</label>
                <textarea
                  value={sqlContent}
                  onChange={(e) => setSqlContent(e.target.value)}
                  placeholder="粘贴新的 DDL SQL..."
                  rows={12}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono outline-none focus:border-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-400"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => { setShowUpload(false); setSqlContent(''); setVersionTag('') }}
                className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                取消
              </button>
              <button
                onClick={handleCreateVersion}
                disabled={!sqlContent.trim() || createVersion.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
              >
                {createVersion.isPending ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteId}
        title="删除版本"
        message="确定要删除此版本吗？"
        confirmLabel="删除"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  )
}
