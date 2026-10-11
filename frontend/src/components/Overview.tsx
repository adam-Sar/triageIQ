import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  Bar,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertTriangle, Gauge, Server, Timer } from 'lucide-react'
import type { ReactNode } from 'react'
import type { StatusResponse } from '../types'
import { Card, CardHeader } from './Card'

function StatCard({
  label,
  value,
  sub,
  icon,
  tone = 'default',
}: {
  label: string
  value: string
  sub: string
  icon: ReactNode
  tone?: 'default' | 'ok' | 'warn' | 'crit'
}) {
  const toneClass = {
    default: 'text-ink',
    ok: 'text-ok',
    warn: 'text-warn',
    crit: 'text-crit',
  }[tone]

  return (
    <Card className="rise p-4">
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-faint">{label}</p>
        <span className="text-faint">{icon}</span>
      </div>
      <p className={`mt-2 font-mono text-[26px] leading-none font-semibold tabular-nums ${toneClass}`}>{value}</p>
      <p className="mt-1.5 text-xs text-muted">{sub}</p>
    </Card>
  )
}

const chartTooltipStyle = {
  backgroundColor: '#131a23',
  border: '1px solid #1d2632',
  borderRadius: 8,
  fontSize: 12,
  fontFamily: '"IBM Plex Mono", monospace',
  color: '#e4eaf2',
}

export function Overview({ status }: { status: StatusResponse | null }) {
  if (!status) {
    return (
      <Card className="flex h-44 items-center justify-center text-sm text-muted">
        Waiting for service data…
      </Card>
    )
  }

  const { metrics, health } = status
  const degraded = health.status !== 'ok'
  const errorPct = (metrics.error_rate * 100).toFixed(1)
  const errorTone = metrics.error_rate >= 0.15 ? 'crit' : metrics.error_rate >= 0.05 ? 'warn' : 'ok'
  const latencyTone = metrics.avg_response_ms >= 1500 ? 'crit' : metrics.avg_response_ms >= 500 ? 'warn' : 'ok'

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Service status"
          value={degraded ? 'DEGRADED' : 'HEALTHY'}
          sub={degraded ? `database: ${health.dependencies.database ?? 'unknown'}` : 'all dependencies reachable'}
          icon={<Server size={15} />}
          tone={degraded ? 'crit' : 'ok'}
        />
        <StatCard
          label="Avg response"
          value={`${metrics.avg_response_ms.toFixed(0)}ms`}
          sub={`p95 ${metrics.p95_response_ms.toFixed(0)}ms`}
          icon={<Timer size={15} />}
          tone={latencyTone}
        />
        <StatCard
          label="Error rate"
          value={`${errorPct}%`}
          sub={`${metrics.error_count} failed of ${metrics.total_requests}`}
          icon={<AlertTriangle size={15} />}
          tone={errorTone}
        />
        <StatCard
          label="Requests"
          value={metrics.total_requests.toLocaleString()}
          sub={`last ${metrics.window_minutes} min (simulated)`}
          icon={<Gauge size={15} />}
        />
      </div>

      <Card className="rise">
        <CardHeader
          title="Latency & errors"
          icon={<Gauge size={15} />}
          subtitle="Averaged over 30-second windows"
        />
        <div className="h-56 p-4 pt-5">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={metrics.timeline} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="#18202b" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: '#5c6879', fontSize: 11, fontFamily: 'IBM Plex Mono' }} axisLine={{ stroke: '#1d2632' }} tickLine={false} />
              <YAxis yAxisId="ms" tick={{ fill: '#5c6879', fontSize: 11, fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="err" orientation="right" tick={{ fill: '#5c6879', fontSize: 11, fontFamily: 'IBM Plex Mono' }} axisLine={false} tickLine={false} width={28} />
              <Tooltip contentStyle={chartTooltipStyle} cursor={{ stroke: '#243044' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#8b98a9' }} />
              <Bar yAxisId="err" dataKey="errors" name="errors" fill="#f87171" fillOpacity={0.55} radius={[2, 2, 0, 0]} maxBarSize={14} />
              <Line yAxisId="ms" type="monotone" dataKey="avg_ms" name="avg ms" stroke="#5b8cff" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}
