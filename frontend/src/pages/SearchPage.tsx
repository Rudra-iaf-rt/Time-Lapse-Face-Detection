import { useState, type FormEvent } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, ErrorState, EmptyState, LoadingState } from '@/components/ui'

export function SearchPage() {
  const [globalId, setGlobalId] = useState('')
  const [cameraId, setCameraId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [eventType, setEventType] = useState('')
  const [result, setResult] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (start && end && new Date(start) > new Date(end)) {
      setError('Start time must be before end time')
      return
    }
    setLoading(true)
    try {
      const data = await api.searchPersons({
        global_id: globalId || undefined,
        camera_id: cameraId || undefined,
        start_time: start ? new Date(start).toISOString() : undefined,
        end_time: end ? new Date(end).toISOString() : undefined,
      })
      setResult(data.data)
      if (eventType) {
        // Event filter is informational when backend search/events is used
        const events = await api.searchPersons({
          global_id: globalId || undefined,
          camera_id: cameraId || undefined,
        })
        setResult({ persons: data.data, event_type_requested: eventType, related: events.data })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Intelligent Search"
        subtitle="Validated filters only — the UI never constructs SQL."
      />
      <Panel className="mb-4">
        <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm">
            Global ID
            <input className="mt-1 w-full rounded-lg border px-3 py-2" value={globalId} onChange={(e) => setGlobalId(e.target.value)} placeholder="PERSON_0007" />
          </label>
          <label className="text-sm">
            Camera
            <input className="mt-1 w-full rounded-lg border px-3 py-2" value={cameraId} onChange={(e) => setCameraId(e.target.value)} placeholder="0" />
          </label>
          <label className="text-sm">
            Event type
            <input className="mt-1 w-full rounded-lg border px-3 py-2" value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="reappeared" />
          </label>
          <label className="text-sm">
            Start time
            <input type="datetime-local" className="mt-1 w-full rounded-lg border px-3 py-2" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="text-sm">
            End time
            <input type="datetime-local" className="mt-1 w-full rounded-lg border px-3 py-2" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <div className="flex items-end">
            <button type="submit" className="rounded-lg bg-[var(--accent)] px-4 py-2 text-white text-sm">
              Run search
            </button>
          </div>
        </form>
      </Panel>
      {error ? <ErrorState message={error} /> : null}
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && !result ? (
          <EmptyState title="No results yet" detail="Submit a validated query." />
        ) : null}
        {result ? (
          <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-[28rem]">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : null}
      </Panel>
    </div>
  )
}
