import { useCallback } from 'react'
import { Header } from './components/Header'
import { Overview } from './components/Overview'
import { ScenarioSelector } from './components/ScenarioSelector'
import { LogViewer } from './components/LogViewer'
import { Investigation } from './components/Investigation'
import { usePolling } from './hooks/usePolling'
import { api } from './lib/api'

export default function App() {
  const status = usePolling(() => api.getStatus(), 5000)

  const refreshAll = useCallback(() => {
    void status.refresh()
  }, [status])

  return (
    <div className="min-h-screen bg-bg">
      <Header status={status.data} onStatusRefresh={refreshAll} />

      <main className="mx-auto grid max-w-6xl gap-4 px-4 py-6 sm:px-6">
        {status.error && (
          <div className="rounded-md border border-crit/30 bg-crit/10 px-4 py-2.5 text-xs text-crit">
            Cannot reach the monitored service: {status.error}
          </div>
        )}

        <Overview status={status.data} />

        <div className="grid gap-4 lg:grid-cols-[minmax(320px,420px)_1fr]">
          <ScenarioSelector status={status.data} onScenarioChanged={refreshAll} />
          <Investigation onInvestigationDone={refreshAll} />
        </div>

        <LogViewer />
      </main>

      <footer className="border-t border-line-soft py-4 text-center text-[11px] text-faint">
        Sentinel MVP · synthetic data from a simulated service · investigation by a LangGraph agent (Google Gemini)
      </footer>
    </div>
  )
}
