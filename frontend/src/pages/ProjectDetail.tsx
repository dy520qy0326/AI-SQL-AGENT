import { useParams } from 'react-router'
import { useProject } from '@/hooks/useProjects'
import { StatsPanel } from '@/components/StatsPanel'
import { SqlUploader } from '@/components/SqlUploader'
import type { UploadResponse } from '@/types/project'

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: project, refetch } = useProject(id!)

  const handleUploadSuccess = (_result: UploadResponse) => {
    refetch()
  }

  return (
    <div className="space-y-6">
      {project && (
        <StatsPanel tableCount={project.table_count} relationCount={project.relation_count} />
      )}

      <div>
        <h2 className="mb-3 text-base font-semibold text-gray-800 dark:text-gray-200">上传 SQL</h2>
        <SqlUploader projectId={id!} onSuccess={handleUploadSuccess} defaultDialect={project?.dialect} />
      </div>

      {project && project.table_count > 0 && (
        <div className="rounded-lg border bg-white p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
          SQL 已解析，请使用上方导航 Tab 查看表结构、关系图、AI 对话等功能。
        </div>
      )}
    </div>
  )
}
