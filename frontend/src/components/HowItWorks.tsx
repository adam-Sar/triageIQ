import { useState } from 'react'
import { ArrowRight, ChevronDown, HelpCircle, RefreshCw } from 'lucide-react'

const STEPS = [
  { title: 'Simulated backend', text: 'A FastAPI service ("shop-backend") generates realistic logs, metrics, and failures.' },
  { title: 'Incident triggered', text: 'You pick a failure scenario; synthetic traffic and errors are produced instantly.' },
  { title: 'LangGraph workflow', text: 'The backend starts a stateful agent graph with a clear begin → investigate → report flow.' },
  { title: 'Gemini picks tools', text: 'The model decides which investigation tool to call next, based on what it has seen.' },
  { title: 'Tools collect evidence', text: 'Real HTTP calls fetch logs, health, metrics, and endpoint responses from the service.' },
  { title: 'Report generated', text: 'Once evidence is sufficient, Gemini writes a structured report: cause, severity, fixes.' },
]

function FlowNode({ label, active }: { label: string; active?: boolean }) {
  return (
    <span
      className={`rounded-md border px-2.5 py-1 font-mono text-[10.5px] ${
        active ? 'border-accent/50 bg-accent-soft/60 text-accent' : 'border-line bg-panel-2 text-muted'
      }`}
    >
      {label}
    </span>
  )
}

export function HowItWorks({ onRefreshStatus }: { onRefreshStatus: () => void }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:text-ink"
        >
          <HelpCircle size={13} />
          How it works
          <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        <button
          onClick={onRefreshStatus}
          title="Refresh service data"
          className="rounded-md border border-line bg-panel p-1.5 text-muted transition-colors hover:text-ink"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      {open && (
        <div className="absolute right-0 top-11 z-30 w-[min(92vw,540px)] rounded-lg border border-line bg-panel p-5 shadow-2xl shadow-black/50">
          <h3 className="text-[13px] font-semibold">How this works</h3>
          <ol className="mt-3 grid gap-2.5">
            {STEPS.map((step, index) => (
              <li key={step.title} className="flex gap-3">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-line bg-panel-2 font-mono text-[10px] text-accent">
                  {index + 1}
                </span>
                <p className="text-xs leading-relaxed text-muted">
                  <span className="font-medium text-ink">{step.title}. </span>
                  {step.text}
                </p>
              </li>
            ))}
          </ol>
          <div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-line-soft pt-4">
            <FlowNode label="incident" />
            <ArrowRight size={11} className="text-faint" />
            <FlowNode label="LangGraph agent" active />
            <ArrowRight size={11} className="text-faint" />
            <FlowNode label="tools" />
            <ArrowRight size={11} className="text-faint" />
            <FlowNode label="evidence" />
            <ArrowRight size={11} className="text-faint" />
            <FlowNode label="report" active />
          </div>
        </div>
      )}
    </div>
  )
}
