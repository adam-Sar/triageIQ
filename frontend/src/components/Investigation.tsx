import { useEffect, useState } from 'react'
import {
  BotMessageSquare,
  ChevronDown,
  CircleCheck,
  CircleX,
  Loader2,
  Sparkles,
  Wrench,
} from 'lucide-react'
import type { Investigation, InvestigationStep } from '../types'
import { api } from '../lib/api'
import { Card, CardHeader } from './Card'
import { ReportCard } from './ReportCard'

function toolLabel(tool: string) {
  return tool === 'finish_investigation' ? 'Investigation complete' : `Called ${tool}`
}

function StepIcon({ tool }: { tool: string }) {
  if (tool === 'finish_investigation') return <CircleCheck size={15} className="text-ok" />
  return <Wrench size={15} className="text-accent" />
}

function StepRow({ step }: { step: InvestigationStep }) {
  const [open, setOpen] = useState(false)
  const hasResult = step.result !== null && step.result !== undefined

  return (
    <li className="relative pb-4 pl-8 last:pb-0">
      <span className="absolute left-[7px] top-1 h-full w-px bg-line last:hidden" aria-hidden />
      <span className="absolute left-0 top-0.5 flex h-4 w-4 items-center justify-center rounded-full border border-line bg-panel-2">
        <StepIcon tool={step.tool} />
      </span>
      <p className="text-[13px] leading-snug">
        <span className="font-medium">{toolLabel(step.tool)}</span>
        <span className="ml-2 font-mono text-[11px] text-faint">step {step.step}</span>
      </p>
      <p className="mt-0.5 text-xs text-muted">{step.summary}</p>
      {hasResult && (
        <>
          <button
            onClick={() => setOpen(!open)}
            className="mt-1 flex items-center gap-1 font-mono text-[11px] text-faint transition-colors hover:text-muted"
          >
            <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
            raw tool result
          </button>
          {open && (
            <pre className="mt-1.5 max-h-52 overflow-auto rounded-md border border-line bg-bg p-3 font-mono text-[10.5px] leading-relaxed text-muted">
              {JSON.stringify(step.result, null, 2)}
            </pre>
          )}
        </>
      )}
    </li>
  )
}

export function Investigation({ onInvestigationDone }: { onInvestigationDone?: () => void }) {
  const [investigation, setInvestigation] = useState<Investigation | null>(null)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const running = investigation?.status === 'pending' || investigation?.status === 'running'

  useEffect(() => {
    if (!investigation || !running) return
    const timer = setInterval(async () => {
      try {
        const updated = await api.getInvestigation(investigation.id)
        setInvestigation(updated)
        if (updated.status === 'completed' || updated.status === 'failed') {
          onInvestigationDone?.()
        }
      } catch {
        /* transient polling errors are ignored; next tick retries */
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [investigation, running, onInvestigationDone])

  async function investigate() {
    setStarting(true)
    setStartError(null)
    try {
      const started = await api.startInvestigation()
      setInvestigation(started)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : 'Failed to start investigation')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="grid gap-4">
      <Card className="rise">
        <CardHeader
          title="AI investigation"
          icon={<Sparkles size={15} />}
          subtitle="A LangGraph agent picks tools, inspects the service, and explains the incident"
          actions={
            <button
              onClick={investigate}
              disabled={starting || running}
              className="flex items-center gap-2 rounded-md border border-accent/40 bg-accent-soft px-3.5 py-1.5 text-[13px] font-semibold text-accent transition-colors hover:border-accent/70 hover:bg-accent/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {running || starting ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {running ? 'Investigating…' : starting ? 'Starting…' : 'Investigate with AI'}
            </button>
          }
        />

        <div className="px-5 py-4">
          {startError && (
            <div className="mb-4 flex items-start gap-2 rounded-md border border-crit/30 bg-crit/10 px-3.5 py-2.5 text-xs text-crit">
              <CircleX size={14} className="mt-0.5 shrink-0" />
              {startError}
            </div>
          )}

          {!investigation && (
            <div className="flex items-center gap-3 rounded-md border border-dashed border-line bg-panel-2/50 px-4 py-5">
              <BotMessageSquare size={18} className="text-faint" />
              <p className="text-xs leading-relaxed text-muted">
                The agent is powered by Google Gemini with real tool access: it calls health checks, metrics,
                logs, and endpoint probes on the simulated service — then writes the report from the evidence it
                collected.
              </p>
            </div>
          )}

          {investigation && (
            <>
              <div className="mb-4 rounded-md border border-line bg-panel-2/50 px-4 py-3">
                <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-faint">Alert context</p>
                <p className="mt-1 font-mono text-[11.5px] leading-relaxed text-muted">{investigation.description}</p>
              </div>

              {investigation.steps.length > 0 && (
                <ol className="mb-2">
                  {investigation.steps.map((step, index) => (
                    <StepRow key={`${step.step}-${index}`} step={step} />
                  ))}
                  {running && (
                    <li className="flex items-center gap-2 pl-8 text-xs text-faint">
                      <Loader2 size={12} className="animate-spin" />
                      agent is thinking…
                    </li>
                  )}
                </ol>
              )}

              {running && investigation.steps.length === 0 && (
                <div className="flex items-center gap-2 py-2 text-xs text-muted">
                  <Loader2 size={13} className="animate-spin text-accent" />
                  Starting the investigation workflow…
                </div>
              )}

              {investigation.status === 'failed' && investigation.error && (
                <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 px-3.5 py-2.5 text-xs text-warn">
                  <CircleX size={14} className="mt-0.5 shrink-0" />
                  <span>{investigation.error}</span>
                </div>
              )}

              {investigation.status === 'completed' && !investigation.report && !investigation.error && (
                <p className="text-xs text-muted">Investigation finished without a report.</p>
              )}
            </>
          )}
        </div>
      </Card>

      {investigation?.report && <ReportCard report={investigation.report} />}
    </div>
  )
}
