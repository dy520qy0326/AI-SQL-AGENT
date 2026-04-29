import { Link, useLocation } from 'react-router'
import { Database, ExternalLink } from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const isProjectPage = location.pathname.startsWith('/projects') && location.pathname !== '/projects'

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Link to="/projects" className="flex items-center gap-2 text-lg font-semibold text-gray-900 no-underline">
              <Database className="h-5 w-5 text-blue-600" />
              AI SQL Agent
            </Link>
            {isProjectPage && (
              <span className="text-sm text-gray-400">
                / <Link to="/projects" className="text-blue-600 no-underline hover:text-blue-800">Projects</Link>
              </span>
            )}
          </div>
          <nav className="flex items-center gap-4 text-sm text-gray-600">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-gray-400 hover:text-gray-600 no-underline"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        {children}
      </main>
    </div>
  )
}
