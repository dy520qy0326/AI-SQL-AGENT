import { useParams } from 'react-router'
import { useProject } from '@/hooks/useProjects'
import { StatsPanel } from '@/components/StatsPanel'
import { SqlUploader } from '@/components/SqlUploader'
import { QueryRelationPanel } from '@/components/QueryRelationPanel'
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
        <>
          <div className="border-t border-gray-200 dark:border-gray-700" />

          <QueryRelationPanel projectId={id!} />
        </>
      )}
    </div>
  )
}
