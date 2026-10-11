import type { ReactNode } from 'react'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={`rounded-lg border border-line bg-panel shadow-[0_1px_0_rgba(255,255,255,0.02)_inset] ${className}`}
    >
      {children}
    </section>
  )
}

export function CardHeader({
  title,
  icon,
  subtitle,
  actions,
}: {
  title: string
  icon: ReactNode
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line-soft px-5 py-3.5">
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="text-accent">{icon}</span>
        <div className="min-w-0">
          <h2 className="text-[13px] font-semibold tracking-wide text-ink">{title}</h2>
          {subtitle && <p className="truncate text-xs text-faint">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}
