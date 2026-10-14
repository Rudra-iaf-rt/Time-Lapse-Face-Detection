import type { ReactNode } from 'react'

function classNames(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') return value.toLocaleString()
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

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
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h2 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">{title}</h2>
        {subtitle ? <p className="mt-1 max-w-3xl text-sm text-[var(--ink-muted)]">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function Panel({
  children,
  title,
  actions,
  className = '',
}: {
  children: ReactNode
  title?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <section
      className={classNames(
        'rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-sm',
        className,
      )}
    >
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title ? <h3 className="text-base font-semibold text-[var(--ink)]">{title}</h3> : <span />}
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      )}
      {children}
    </section>
  )
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <div className="text-base font-medium text-[var(--ink)]">{title}</div>
      {detail ? <p className="max-w-md text-sm text-[var(--ink-muted)]">{detail}</p> : null}
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <span className="font-medium">Error:</span> {message}
    </div>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-sm text-[var(--ink-muted)]">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--accent)]" />
      {label}
    </div>
  )
}

export function Toast({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="fixed bottom-4 right-4 z-50 rounded-lg bg-[var(--ink)] px-4 py-3 text-sm text-white shadow-lg">
      {message}
    </div>
  )
}

export function StatCard({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string
  value: string | number
  hint?: string
  tone?: 'default' | 'ok' | 'warn' | 'danger'
}) {
  const toneClass =
    tone === 'ok'
      ? 'text-emerald-700'
      : tone === 'warn'
        ? 'text-amber-700'
        : tone === 'danger'
          ? 'text-red-700'
          : 'text-[var(--ink)]'

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]">{label}</div>
      <div className={classNames('mt-2 text-2xl font-semibold', toneClass)}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-[var(--ink-muted)]">{hint}</div> : null}
    </div>
  )
}

export function StatusBadge({
  value,
}: {
  value: unknown
}) {
  const text = String(value ?? '—')
  const lower = text.toLowerCase()
  const tone =
    lower.includes('active') || lower.includes('ready') || lower.includes('ok')
      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
      : lower.includes('lost') || lower.includes('warn') || lower.includes('degraded')
        ? 'bg-amber-50 text-amber-800 border-amber-200'
        : lower.includes('error') || lower.includes('fail') || lower.includes('blocked')
          ? 'bg-red-50 text-red-800 border-red-200'
          : 'bg-slate-50 text-slate-700 border-slate-200'

  return (
    <span className={classNames('inline-flex rounded-full border px-2.5 py-1 text-xs font-medium', tone)}>
      {text}
    </span>
  )
}

export function KeyValueList({
  data,
  emptyTitle = 'No data',
  emptyDetail,
  columns = 2,
}: {
  data: Record<string, unknown> | null | undefined
  emptyTitle?: string
  emptyDetail?: string
  columns?: 1 | 2
}) {
  const entries = Object.entries(data || {}).sort(([a], [b]) => a.localeCompare(b))

  if (!entries.length) {
    return <EmptyState title={emptyTitle} detail={emptyDetail} />
  }

  return (
    <dl className={classNames('grid gap-3 text-sm', columns === 1 ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2')}>
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg border border-[var(--line)] bg-[var(--bg-elevated)] p-3">
          <dt className="text-xs font-medium uppercase tracking-wide text-[var(--ink-muted)]">{key}</dt>
          <dd className="mt-1 break-words text-[var(--ink)]">
            {typeof value === 'object' && value !== null ? (
              <pre className="max-h-48 overflow-auto text-xs">{JSON.stringify(value, null, 2)}</pre>
            ) : (
              formatValue(value)
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}

export function DataTable({
  rows,
  columns,
  emptyTitle = 'No records',
  emptyDetail,
  onRowClick,
}: {
  rows: Array<Record<string, unknown>>
  columns?: string[]
  emptyTitle?: string
  emptyDetail?: string
  onRowClick?: (row: Record<string, unknown>) => void
}) {
  const cols = columns || (rows.length ? Object.keys(rows[0]) : [])

  if (!rows.length) {
    return <EmptyState title={emptyTitle} detail={emptyDetail} />
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-max border-separate border-spacing-0 text-sm">
        <thead>
          <tr>
            {cols.map((col) => (
              <th
                key={col}
                className="sticky top-0 border-b border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--ink-muted)]"
              >
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={String(row.id ?? row.global_id ?? idx)}
              className={classNames(
                'border-b border-[var(--line)]/60',
                onRowClick ? 'cursor-pointer hover:bg-[var(--bg-elevated)]' : 'hover:bg-[var(--bg-elevated)]/60',
              )}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {cols.map((col) => (
                <td key={col} className="px-3 py-2 align-top text-[var(--ink)]">
                  {col.toLowerCase().includes('status') ? (
                    <StatusBadge value={row[col]} />
                  ) : typeof row[col] === 'object' && row[col] !== null ? (
                    <span className="font-mono text-xs">{JSON.stringify(row[col])}</span>
                  ) : (
                    formatValue(row[col])
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Pagination({
  page,
  perPage,
  total,
  onChange,
}: {
  page: number
  perPage: number
  total: number
  onChange: (page: number) => void
}) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(perPage, 1)))
  return (
    <div className="mt-4 flex items-center justify-between gap-2 text-sm text-[var(--ink-muted)]">
      <span>
        Page {page} of {totalPages} ({total.toLocaleString()} total)
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          className="rounded-lg border border-[var(--line)] px-3 py-1.5 disabled:opacity-40"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          className="rounded-lg border border-[var(--line)] px-3 py-1.5 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}