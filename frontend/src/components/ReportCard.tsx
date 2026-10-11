import { BadgeCheck, ClipboardList, FileSearch, ListChecks } from 'lucide-react'
import type { IncidentReport, Severity } from '../types'
import { Card, CardHeader } from './Card'

const SEVERITY_STYLES: Record<Severity, { label: string; className: string }> = {
  healthy: { label: 'Healthy', className: 'border-ok/30 bg-ok/10 text-ok' },
  low: { label: 'Low', className: 'border-ok/30 bg-ok/10 text-ok' },
  medium: { label: 'Medium', className: 'border-warn/30 bg-warn/10 text-warn' },
  high: { label: 'High', className: 'border-crit/30 bg-crit/10 text-crit' },
  critical: { label: 'Critical', className: 'border-crit/40 bg-crit/15 text-crit' },
}

export function ReportCard({ report }: { report: IncidentReport }) {
  const severity = SEVERITY_STYLES[report.severity] ?? SEVERITY_STYLES.medium
  const confidencePct = Math.round(report.confidence * 100)

  return (
    <Card className="rise">
      <CardHeader
        title="Incident report"
        icon={<ClipboardList size={15} />}
        subtitle={report.affected_service}
      />
      <div className="grid gap-5 px-5 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <h3 className="text-[15px] font-semibold leading-snug">{report.title}</h3>
          <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${severity.className}`}>
            {severity.label}
          </span>
        </div>

        <p className="text-[13px] leading-relaxed text-muted">{report.summary}</p>

        <div className="rounded-md border border-line bg-panel-2/50 p-4">
          <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-faint">
            <FileSearch size={12} /> Probable root cause
          </p>
          <p className="mt-2 border-l-2 border-accent/50 pl-3 text-[13px] leading-relaxed text-ink">
            {report.root_cause}
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <div>
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-faint">
              <BadgeCheck size={12} /> Evidence collected
            </p>
            <ul className="mt-2 grid gap-1.5">
              {report.evidence.map((item, index) => (
                <li key={index} className="flex gap-2 text-xs leading-relaxed text-muted">
                  <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-faint">
              <ListChecks size={12} /> Recommended actions
            </p>
            <ol className="mt-2 grid gap-1.5">
              {report.recommended_actions.map((action, index) => (
                <li key={index} className="flex gap-2 text-xs leading-relaxed text-muted">
                  <span className="font-mono text-faint">{index + 1}.</span>
                  {action}
                </li>
              ))}
            </ol>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-[11px] text-faint">
            <span className="font-medium uppercase tracking-[0.12em]">Estimated confidence</span>
            <span className="font-mono">{confidencePct}%</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-panel-2">
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-700"
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <p className="mt-1.5 text-[10.5px] text-faint">
            The agent's own estimate based on the evidence it gathered — treat it as a signal, not a guarantee.
          </p>
        </div>
      </div>
    </Card>
  )
}
