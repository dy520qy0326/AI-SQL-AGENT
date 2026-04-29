import { NavLink } from 'react-router'
import { Table2, Network, MessageSquare, FileText, GitCompare, Home } from 'lucide-react'

const tabs = [
  { path: '', label: '概览', icon: Home },
  { path: 'tables', label: '表结构', icon: Table2 },
  { path: 'graph', label: '关系图', icon: Network },
  { path: 'ai', label: 'AI 对话', icon: MessageSquare },
  { path: 'docs', label: '文档', icon: FileText },
  { path: 'versions', label: '版本', icon: GitCompare },
]

interface NavTabsProps {
  projectId: string
}

export function NavTabs({ projectId }: NavTabsProps) {
  return (
    <nav className="-mb-px flex gap-1 overflow-x-auto">
      {tabs.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path ? `/projects/${projectId}/${tab.path}` : `/projects/${projectId}`}
          end={tab.path === ''}
          className="flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium text-gray-500 no-underline transition hover:text-gray-700 aria-current-page:border-blue-600 aria-current-page:text-blue-600"
        >
          <tab.icon className="h-4 w-4" />
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
