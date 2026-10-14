import { useAuth } from '@/store/auth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PageHeader, Panel, EmptyState, PersonImage } from '@/components/ui'

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
              <li key={idx} className="flex gap-3 rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
                {ev.crop_url ? (
                  <PersonImage src={String(ev.crop_url)} alt={String(ev.global_id || 'event')} className="h-14 w-14 flex-none" />
                ) : (
                  <div className="flex h-14 w-14 flex-none items-center justify-center rounded-lg border border-dashed border-[var(--line)] text-xs text-[var(--ink-muted)]">
                    No image
                  </div>
                )}
                <div className="min-w-0">
                  <div className="font-medium">{ev.event}</div>
                  <div className="mt-1 text-xs text-[var(--ink-muted)]">
                    global_id={ev.global_id || '—'} · camera_id={String(ev.camera_id ?? '—')} ·{' '}
                    {ev.timestamp || '—'}
                  </div>
                  {ev.confidence != null ? (
                    <div className="mt-1 text-xs text-[var(--ink-muted)]">
                      confidence={Number(ev.confidence).toFixed(2)}
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}
