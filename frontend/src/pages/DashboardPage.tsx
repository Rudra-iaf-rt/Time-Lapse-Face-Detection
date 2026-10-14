import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, StatCard, DataTable, KeyValueList, Toast } from '@/components/ui'
import type { PersonRow } from '@/types'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAuth } from '@/store/auth'

export function DashboardPage() {
  const { username } = useAuth()
  const [persons, setPersons] = useState<PersonRow[]>([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [toast] = useState<string | null>(null)
  const { status, events } = useWebSocket(`${username || 'operator'}-dash`)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [p, s] = await Promise.all([
          api.listPersons(1, 8),
          api.analyticsSummary().catch(() => null),
        ])
        if (cancelled) return
        setPersons(p.data?.items || [])
        setTotal(p.data?.total || 0)
        setStats((s?.data as Record<string, unknown>) || null)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load dashboard')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Live identity overview from FastAPI and IdentityStore. No fabricated metrics."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}

      <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Loaded identities" value={persons.length} hint="Current page" />
        <StatCard label="Total identities" value={total} hint="IdentityStore total" />
        <StatCard label="Live WebSocket" value={status} hint="Connection status" />
        <StatCard label="Recent events" value={events.length} hint="In memory" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Recent persons" className="lg:col-span-2">
          {!loading && persons.length === 0 ? (
            <EmptyState
              title="No identities yet"
              detail="Run the sample pipeline or wait for detections. Streamlit SQLite data appears here when present."
            />
          ) : (
            <DataTable
              rows={persons as Array<Record<string, unknown>>}
              columns={['global_id', 'status', 'last_camera', 'last_seen']}
              emptyTitle="No identities yet"
            />
          )}
          {persons.length ? (
            <div className="mt-3 text-right">
              <Link to="/persons" className="text-sm text-[var(--accent)] underline">
                View all persons
              </Link>
            </div>
          ) : null}
        </Panel>

        <Panel title="Live events">
          <div className="mb-3 text-xs text-[var(--ink-muted)]">WebSocket: {status}</div>
          {events.length === 0 ? (
            <EmptyState title="No live events" detail="Connects to VITE_WS_URL. Events appear only when the backend broadcasts them." />
          ) : (
            <ul className="max-h-80 space-y-2 overflow-auto text-sm">
              {events.slice(0, 12).map((ev, i) => (
                <li key={`${ev.event}-${i}`} className="rounded-md bg-[var(--bg-elevated)] px-3 py-2">
                  <div className="font-medium">{ev.event}</div>
                  <div className="mt-1 text-xs text-[var(--ink-muted)]">
                    {ev.global_id || '—'} · {String(ev.camera_id ?? '—')} · {ev.timestamp || '—'}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Analytics summary" className="lg:col-span-3">
          {stats ? (
            <KeyValueList data={stats as Record<string, unknown>} />
          ) : (
            <EmptyState title="Summary unavailable" detail="Backend /api/analytics/summary returned no data or is unreachable." />
          )}
        </Panel>
      </div>
      <Toast message={toast} />
    </div>
  )
}