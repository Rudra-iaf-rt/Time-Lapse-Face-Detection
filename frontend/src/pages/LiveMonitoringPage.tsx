import { useAuth } from '@/store/auth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PageHeader, Panel, EmptyState } from '@/components/ui'

export function LiveMonitoringPage() {
  const { username } = useAuth()
  const { status, events, error, reconnect } = useWebSocket(`${username || 'op'}-live`)

  return (
    <div>
      <PageHeader
        title="Live Monitoring"
        subtitle="Real WebSocket events only — no simulated detections."
        actions={
          <button
            type="button"
            onClick={reconnect}
            className="rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-sm"
          >
            Reconnect
          </button>
        }
      />
      <Panel>
        <div className="flex gap-4 text-sm mb-4">
          <span>Status: <strong>{status}</strong></span>
          {error ? <span className="text-red-700">{error}</span> : null}
        </div>
        {events.length === 0 ? (
          <EmptyState
            title="Waiting for events"
            detail="Events such as person_detected, identity_matched, person_reappeared appear when published by the pipeline/API."
          />
        ) : (
          <ul className="space-y-2">
            {events.map((ev, idx) => (
              <li key={idx} className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
                <div className="font-medium">{ev.event}</div>
                <div className="text-[var(--ink-muted)] text-xs mt-1">
                  global_id={ev.global_id || '—'} · camera_id={String(ev.camera_id ?? '—')} ·{' '}
                  {ev.timestamp}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}
