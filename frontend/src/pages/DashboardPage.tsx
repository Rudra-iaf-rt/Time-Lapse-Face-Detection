import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'
import type { PersonRow } from '@/types'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAuth } from '@/store/auth'

export function DashboardPage() {
  const { username } = useAuth()
  const [persons, setPersons] = useState<PersonRow[]>([])
  const [stats, setStats] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
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
        subtitle="Live identity overview from FastAPI + IdentityStore. No fabricated metrics."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <h3 className="font-medium mb-3">Recent persons</h3>
          {!loading && persons.length === 0 ? (
            <EmptyState
              title="No identities yet"
              detail="Run the sample pipeline or wait for detections. Streamlit SQLite data appears here when present."
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--ink-muted)] border-b border-[var(--line)]">
                  <th className="py-2">global_id</th>
                  <th>Status</th>
                  <th>Camera</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {persons.map((p) => (
                  <tr key={p.global_id} className="border-b border-[var(--line)]/70">
                    <td className="py-2 font-medium">{p.global_id}</td>
                    <td>{p.status || '—'}</td>
                    <td>{String(p.last_camera ?? '—')}</td>
                    <td className="text-right">
                      <Link className="text-[var(--accent)] underline" to={`/persons/${p.global_id}`}>
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel>
          <h3 className="font-medium mb-3">Live events</h3>
          <div className="text-xs text-[var(--ink-muted)] mb-2">WebSocket: {status}</div>
          {events.length === 0 ? (
            <EmptyState title="No live events" detail="Connects to VITE_WS_URL. Events appear only when the backend broadcasts them." />
          ) : (
            <ul className="space-y-2 max-h-80 overflow-auto text-sm">
              {events.slice(0, 12).map((ev, i) => (
                <li key={`${ev.event}-${i}`} className="rounded-md bg-[var(--bg-elevated)] px-3 py-2">
                  <div className="font-medium">{ev.event}</div>
                  <div className="text-xs text-[var(--ink-muted)]">
                    {ev.global_id || '—'} · {ev.camera_id ?? '—'} · {ev.timestamp || ''}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel className="lg:col-span-3">
          <h3 className="font-medium mb-2">Analytics summary</h3>
          {stats ? (
            <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg">
              {JSON.stringify(stats, null, 2)}
            </pre>
          ) : (
            <EmptyState title="Summary unavailable" detail="Backend /api/analytics/summary returned no data or is unreachable." />
          )}
        </Panel>
      </div>
    </div>
  )
}
