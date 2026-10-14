import { useState, type FormEvent } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, ErrorState, EmptyState, LoadingState, DataTable, KeyValueList } from '@/components/ui'

function extractRows(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) return value as Array<Record<string, unknown>>
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>
    for (const key of ['results', 'items', 'rows', 'data', 'sightings', 'sqlite_events']) {
      if (Array.isArray(obj[key])) return obj[key] as Array<Record<string, unknown>>
    }
  }
  return []
}

function extractSummary(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const obj = value as Record<string, unknown>
  const summary = Object.fromEntries(
    Object.entries(obj).filter(([, val]) => !Array.isArray(val)),
  )
  return Object.keys(summary).length ? summary : null
}

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
      const primary = await api.searchPersons({
        global_id: globalId || undefined,
        camera_id: cameraId || undefined,
        start_time: start ? new Date(start).toISOString() : undefined,
        end_time: end ? new Date(end).toISOString() : undefined,
      })
      let data: unknown = primary.data
      if (eventType) {
        const related = await api.searchPersons({
          global_id: globalId || undefined,
          camera_id: cameraId || undefined,
        }).catch(() => null)
        data = { primary: primary.data, related: related?.data ?? null, event_type_requested: eventType }
      }
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const rows = extractRows(result)
  const summary = extractSummary(result)

  return (
    <div>
      <PageHeader
        title="Intelligent Search"
        subtitle="Validated filters only. The UI never constructs SQL."
      />
      <Panel className="mb-4" title="Search filters">
        <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm">
            Global ID
            <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={globalId} onChange={(e) => setGlobalId(e.target.value)} placeholder="PERSON_DB5270AE" />
          </label>
          <label className="text-sm">
            Camera
            <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={cameraId} onChange={(e) => setCameraId(e.target.value)} placeholder="0" />
          </label>
          <label className="text-sm">
            Event type
            <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="reappeared" />
          </label>
          <label className="text-sm">
            Start time
            <input type="datetime-local" className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="text-sm">
            End time
            <input type="datetime-local" className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <div className="flex items-end">
            <button type="submit" className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white">
              Run search
            </button>
          </div>
        </form>
      </Panel>
      {error ? <ErrorState message={error} /> : null}
      <Panel title="Results">
        {loading ? <LoadingState /> : null}
        {!loading && !result ? <EmptyState title="No results yet" detail="Submit a validated query." /> : null}
        {!loading && rows.length ? (
          <>
            <div className="mb-3 text-sm text-[var(--ink-muted)]">{rows.length.toLocaleString()} result rows</div>
            <DataTable rows={rows} />
          </>
        ) : null}
        {!loading && summary ? (
          <div className="mt-4">
            <h4 className="mb-2 text-sm font-medium text-[var(--ink)]">Result metadata</h4>
            <KeyValueList data={summary} />
          </div>
        ) : null}
        {!loading && result && !rows.length && !summary ? (
          <pre className="max-h-[28rem] overflow-auto rounded-lg bg-[var(--bg-elevated)] p-3 text-xs">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : null}
      </Panel>
    </div>
  )
}