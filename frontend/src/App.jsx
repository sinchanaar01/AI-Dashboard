import { lazy, Suspense, useState } from 'react'
import Sidebar from './components/Sidebar'

const Overview = lazy(() => import('./pages/Overview'))
const Predictions = lazy(() => import('./pages/Predictions'))
const Chat = lazy(() => import('./pages/Chat'))

function App() {
  const [page, setPage] = useState('overview')

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 font-sans text-slate-200 selection:bg-indigo-500/30 lg:flex-row">
      <Sidebar page={page} setPage={setPage} />
      <main className="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
        <Suspense fallback={<p role="status" className="py-16 text-center text-sm text-slate-400">Loading dashboard page…</p>}>
          {page === 'overview' && <Overview />}
          {page === 'chat' && <Chat />}
          {page === 'predictions' && <Predictions />}
        </Suspense>
      </main>
    </div>
  )
}

export default App