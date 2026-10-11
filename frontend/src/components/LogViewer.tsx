import { useMemo, useState } from 'react'
import { ScrollText } from 'lucide-react'
import type { LogEntry, LogLevel } from '../types'
import { usePolling } from '../hooks/usePolling'
import { api } from '../lib/api'
import { Card, CardHeader } from './Card'

const LEVEL_STYLES: Record<LogLevel, string> = {
  INFO: 'text-ok border-ok/25 bg-ok/10',
  WARNING: 'text-warn border-warn/25 bg-warn/10',
  ERROR: 'text-crit border-crit/25 bg-crit/10',
}

function formatTime(iso: string) {
  return iso.slice(11, 19)
}

function statusColor(entry: LogEntry) {
  if (entry.status_code >= 500) return 'text-crit'
  if (entry.status_code >= 400) return 'text-warn'
  return 'text-faint'
}

export function LogViewer() {
  const [filter, setFilter] = useState<'ALL' | LogLevel>('ALL')
  const { data, error } = usePolling(() => api.getLogs(150), 5000)

  const logs = useMemo(() => {
    const all = data?.logs ?? []
    return filter === 'ALL' ? all : all.filter((log) => log.level === filter)
  }, [data, filter])

  const counts = useMemo(() => {
    const all = data?.logs ?? []
    return {
      ALL: all.length,
      INFO: all.filter((l) => l.level === 'INFO').length,
      WARNING: all.filter((l) => l.level === 'WARNING').length,
      ERROR: all.filter((l) => l.level === 'ERROR').length,
    }
  }, [data])

  return (
    <Card className="rise">
      <CardHeader
        title="Application logs"
        icon={<ScrollText size={15} />}
        subtitle="Newest first · simulated service output"
        actions={
          <div className="flex gap-1 rounded-md border border-line bg-panel-2 p-0.5">
            {(['ALL', 'INFO', 'WARNING', 'ERROR'] as const).map((level) => (
              <button
                key={level}
                onClick={() => setFilter(level)}
                className={`rounded px-2 py-1 font-mono text-[11px] transition-colors ${
                  filter === level ? 'bg-accent-soft text-ink' : 'text-faint hover:text-muted'
                }`}
              >
                {level === 'ALL' ? 'ALL' : level.slice(0, 4)}
                <span className="ml-1 text-[10px] opacity-60">{counts[level]}</span>
              </button>
            ))}
          </div>
        }
      />
      {error ? (
        <p className="px-5 py-8 text-center text-sm text-crit">{error}</p>
      ) : (
        <div className="max-h-[420px] overflow-y-auto font-mono text-[11.5px] leading-relaxed">
          {logs.length === 0 ? (
            <p className="px-5 py-8 text-center text-muted">No log entries match this filter.</p>
          ) : (
            <table className="w-full border-collapse">
              <tbody>
                {logs.map((log) => (
                  <tr key={log.request_id + log.timestamp} className="border-b border-line-soft/60 hover:bg-panel-2/60">
                    <td className="whitespace-nowrap py-1.5 pl-5 pr-3 align-top text-faint">{formatTime(log.timestamp)}</td>
                    <td className="py-1.5 pr-3 align-top">
                      <span className={`inline-block rounded border px-1.5 py-px text-[10px] font-semibold ${LEVEL_STYLES[log.level]}`}>
                        {log.level}
                      </span>
                    </td>
                    <td className="hidden whitespace-nowrap py-1.5 pr-3 align-top text-muted md:table-cell">{log.service}</td>
                    <td className="hidden whitespace-nowrap py-1.5 pr-3 align-top text-faint lg:table-cell">
                      {log.endpoint !== '-' && log.status_code > 0 && (
                        <>
                          <span className="text-muted">{log.method}</span>{' '}
                          <span className="text-muted/80">{log.endpoint}</span>{' '}
                          <span className={statusColor(log)}>{log.status_code}</span>{' '}
                          <span className="text-faint">{log.duration_ms.toFixed(0)}ms</span>
                        </>
                      )}
                    </td>
                    <td className="py-1.5 pr-5 align-top text-ink/90">{log.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Card>
  )
}
