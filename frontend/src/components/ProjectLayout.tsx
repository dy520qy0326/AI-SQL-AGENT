import { Outlet, useParams, Navigate } from 'react-router'
import { Layout } from '@/components/Layout'
import { NavTabs } from '@/components/NavTabs'
import { useProject } from '@/hooks/useProjects'
import { Loader2 } from 'lucide-react'

export function ProjectLayout() {
  const { id } = useParams<{ id: string }>()
  const { data: project, isLoading } = useProject(id!)

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      </Layout>
    )
  }

  if (!project) {
    return <Navigate to="/projects" replace />
  }

  return (
    <Layout>
      <div className="mb-1">
        <h1 className="text-xl font-bold text-gray-900">{project.name}</h1>
        {project.description && (
          <p className="mt-1 text-sm text-gray-500">{project.description}</p>
        )}
      </div>
      <div className="mb-6 border-b border-gray-200">
        <NavTabs projectId={id!} />
      </div>
      <Outlet />
    </Layout>
  )
}
