import { Activity } from 'lucide-react'
import type { StatusResponse } from '../types'
import { HowItWorks } from './HowItWorks'

export function Header({ status, onStatusRefresh }: { status: StatusResponse | null; onStatusRefresh: () => void }) {
  const degraded = status ? status.health.status !== 'ok' : false
  const statusLabel = status ? (degraded ? 'Degraded' : 'Operational') : 'Connecting…'
  const dotColor = !status ? 'bg-faint' : degraded ? 'bg-crit pulse-dot' : 'bg-ok'

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-line bg-panel-2 text-accent">
            <Activity size={16} strokeWidth={2.2} />
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold tracking-tight">triageIQ</span>
              <span className="hidden text-[11px] text-faint sm:inline">AI incident investigation</span>
            </div>
            <p className="font-mono text-[11px] text-muted">
              service: <span className="text-ink">shop-backend</span>
              <span className="text-faint"> · simulated</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-1.5">
            <span className={`h-2 w-2 rounded-full ${dotColor}`} />
            <span className="text-xs font-medium">{statusLabel}</span>
            {status && (
              <span className="hidden font-mono text-[11px] text-faint md:inline">
                {status.health_response_time_ms.toFixed(0)}ms
              </span>
            )}
          </div>
          <HowItWorks onRefreshStatus={onStatusRefresh} />
        </div>
      </div>
    </header>
  )
}
