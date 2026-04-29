import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProjectList } from '@/pages/ProjectList'
import { ProjectLayout } from '@/components/ProjectLayout'
import { ProjectDetail } from '@/pages/ProjectDetail'
import { TablesView } from '@/pages/TablesView'
import { TableDetail } from '@/pages/TableDetail'
import { GraphView } from '@/pages/GraphView'
import { AiChat } from '@/pages/AiChat'
import { DocsView } from '@/pages/DocsView'
import { DocPreview } from '@/pages/DocPreview'
import { VersionsView } from '@/pages/VersionsView'
import { DiffView } from '@/pages/DiffView'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectList />} />
          <Route path="/projects/:id" element={<ProjectLayout />}>
            <Route index element={<ProjectDetail />} />
            <Route path="tables" element={<TablesView />} />
            <Route path="tables/:tableId" element={<TableDetail />} />
            <Route path="graph" element={<GraphView />} />
            <Route path="ai" element={<AiChat />} />
            <Route path="docs" element={<DocsView />} />
            <Route path="docs/:docId" element={<DocPreview />} />
            <Route path="versions" element={<VersionsView />} />
            <Route path="diff/:diffId" element={<DiffView />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
