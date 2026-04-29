import { Link, useLocation } from 'react-router'
import { Database, ExternalLink, Sun, Moon } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { toggle, resolved } = useTheme()
  const isProjectPage = location.pathname.startsWith('/projects') && location.pathname !== '/projects'

  return (
    <div className="min-h-screen bg-gray-50 transition-colors dark:bg-gray-950">
      <header className="border-b bg-white shadow-sm transition-colors dark:border-gray-700 dark:bg-gray-900">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Link to="/projects" className="flex items-center gap-2 text-lg font-semibold text-gray-900 no-underline dark:text-gray-100">
              <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              AI SQL Agent
            </Link>
            {isProjectPage && (
              <span className="text-sm text-gray-400 dark:text-gray-500">
                / <Link to="/projects" className="text-blue-600 no-underline hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">Projects</Link>
              </span>
            )}
          </div>
          <nav className="flex items-center gap-4 text-sm text-gray-600">
            <button
              onClick={toggle}
              className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors dark:text-gray-500 dark:hover:bg-gray-800 dark:hover:text-gray-300 cursor-pointer"
              title={resolved === 'dark' ? '切换亮色模式' : '切换暗色模式'}
            >
              {resolved === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-gray-400 hover:text-gray-600 no-underline dark:text-gray-500 dark:hover:text-gray-300"
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
