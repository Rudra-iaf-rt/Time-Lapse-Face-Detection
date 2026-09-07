import type { ReactNode } from 'react'

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-[var(--ink-muted)]">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  )
}

export function Panel({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={`rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-sm ${className}`}
    >
      {children}
    </section>
  )
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="py-12 text-center text-[var(--ink-muted)]">
      <div className="font-medium text-[var(--ink)]">{title}</div>
      {detail ? <p className="mt-2 text-sm max-w-md mx-auto">{detail}</p> : null}
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {message}
    </div>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return <div className="py-10 text-center text-sm text-[var(--ink-muted)]">{label}</div>
}

export function Toast({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="fixed bottom-4 right-4 z-50 rounded-lg bg-[var(--ink)] px-4 py-2 text-sm text-white shadow-lg">
      {message}
    </div>
  )
}
