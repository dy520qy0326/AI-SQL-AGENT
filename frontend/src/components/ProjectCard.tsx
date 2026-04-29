import { Link } from 'react-router'
import { Table2, GitCompare } from 'lucide-react'
import type { Project } from '@/types/project'
import { formatDate } from '@/lib/utils'

interface ProjectCardProps {
  project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link
      to={`/projects/${project.id}`}
      className="block rounded-lg border bg-white p-5 shadow-sm transition hover:shadow-md hover:border-blue-200 no-underline flex flex-col h-full dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-700"
    >
      <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2 truncate" title={project.name}>
        {project.name}
      </h3>
      <div className="min-h-[2.5rem] mb-3">
        {project.description && (
          <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2" title={project.description}>
            {project.description}
          </p>
        )}
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-gray-500 mt-auto">
        <span className="flex items-center gap-1">
          <Table2 className="h-3.5 w-3.5" />
          {project.table_count} 张表
        </span>
        <span className="flex items-center gap-1">
          <GitCompare className="h-3.5 w-3.5" />
          {project.relation_count} 个关系
        </span>
        <span className="ml-auto">
          {formatDate(project.created_at)}
        </span>
      </div>
    </Link>
  )
}
