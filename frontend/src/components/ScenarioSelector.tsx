import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  Database,
  KeyRound,
  Play,
  ShieldCheck,
  Timer,
  TriangleAlert,
} from 'lucide-react'
import type { ScenarioInfo, StatusResponse } from '../types'
import { api } from '../lib/api'
import { Card, CardHeader } from './Card'

const SCENARIO_ICONS: Record<string, ReactNode> = {
  healthy: <ShieldCheck size={15} />,
  db_timeout: <Database size={15} />,
  high_latency: <Timer size={15} />,
  auth_failure: <KeyRound size={15} />,
  service_failure: <TriangleAlert size={15} />,
}

export function ScenarioSelector({
  status,
  onScenarioChanged,
}: {
  status: StatusResponse | null
  onScenarioChanged: () => void
}) {
  const [selected, setSelected] = useState('db_timeout')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scenarios: ScenarioInfo[] = [
    { id: 'healthy', name: 'Healthy operation', description: 'Normal traffic, low latency, almost no errors.' },
    { id: 'db_timeout', name: 'Database timeout', description: 'Connections time out; HTTP 503s and pool exhaustion.' },
    { id: 'high_latency', name: 'High latency', description: 'Slow but successful requests with slow-query warnings.' },
    { id: 'auth_failure', name: 'Authentication failures', description: 'Requests rejected with HTTP 401 and auth errors.' },
    { id: 'service_failure', name: 'Internal server errors', description: 'Unhandled exceptions producing HTTP 500s.' },
  ]

  const activeScenario = status?.scenario.id

  async function simulate() {
    setSubmitting(true)
    setError(null)
    try {
      await api.activateScenario(selected)
      onScenarioChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate scenario')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="rise">
      <CardHeader
        title="Incident simulation"
        icon={<Play size={15} />}
        subtitle={
          activeScenario
            ? `Active: ${scenarios.find((s) => s.id === activeScenario)?.name ?? activeScenario}`
            : 'Pick a failure mode and generate synthetic traffic'
        }
      />
      <div className="grid gap-2 p-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        {scenarios.map((scenario) => {
          const isSelected = scenario.id === selected
          const isActive = scenario.id === activeScenario
          return (
            <button
              key={scenario.id}
              onClick={() => setSelected(scenario.id)}
              className={`group flex items-start gap-3 rounded-lg border px-3.5 py-3 text-left transition-colors duration-150 ${
                isSelected
                  ? 'border-accent/60 bg-accent-soft/40'
                  : 'border-line bg-panel-2 hover:border-faint/50 hover:bg-panel-2/70'
              }`}
            >
              <span className={`mt-0.5 ${isSelected ? 'text-accent' : 'text-faint group-hover:text-muted'}`}>
                {SCENARIO_ICONS[scenario.id]}
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-2 text-[13px] font-medium">
                  {scenario.name}
                  {isActive && (
                    <span className="rounded border border-line bg-bg px-1.5 py-0.5 font-mono text-[10px] text-muted">
                      active
                    </span>
                  )}
                </span>
                <span className="mt-0.5 block text-xs leading-snug text-muted">{scenario.description}</span>
              </span>
            </button>
          )
        })}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-soft px-4 py-3">
        <p className="text-[11px] text-faint">
          Generates a fresh, deterministic batch of logs &amp; metrics for the last 5 minutes.
        </p>
        <button
          onClick={simulate}
          disabled={submitting}
          className="flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-[13px] font-semibold text-bg transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <TriangleAlert size={14} strokeWidth={2.4} />
          {submitting ? 'Generating…' : 'Simulate Incident'}
        </button>
      </div>
      {error && <p className="border-t border-line-soft px-4 py-2 text-xs text-crit">{error}</p>}
    </Card>
  )
}
