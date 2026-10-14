import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, KeyValueList } from '@/components/ui'

function extractEvents(data: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(data)) return data as Array<Record<string, unknown>>
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>
    for (const key of ['events', 'sightings', 'sqlite_events', 'rows', 'results', 'items']) {
      if (Array.isArray(obj[key])) return obj[key] as Array<Record<string, unknown>>
    }
  }
  return []
}

function extractSummary(data: unknown): Record<string, unknown> | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null
  const obj = data as Record<string, unknown>
  const summary = Object.fromEntries(Object.entries(obj).filter(([, value]) => !Array.isArray(value)))
  return Object.keys(summary).length ? summary : null
}

export function TimelinePage() {
  const [globalId, setGlobalId] = useState('')
  const [data, setData] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function load(id: string) {
    if (!id.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.personTimeline(id.trim())
      setData(res.data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Timeline unavailable')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    api
      .listPersons(1, 1)
      .then((r) => {
        const id = r.data?.items?.[0]?.global_id
        if (id) {
          setGlobalId(id)
          void load(id)
        }
      })
      .catch(() => undefined)
  }, [])

  const rows = extractEvents(data)
  const summary = extractSummary(data)

  return (
    <div>
      <PageHeader title="Timeline" subtitle="Camera journey and sightings for a global_id." />
      <Panel className="mb-4" title="Load timeline">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void load(globalId)
          }}
        >
          <input
            className="flex-1 rounded-lg border border-[var(--line)] px-3 py-2 text-sm"
            value={globalId}
            onChange={(e) => setGlobalId(e.target.value)}
            placeholder="PERSON_DB5270AE"
          />
          <button type="submit" className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white">
            Load
          </button>
        </form>
      </Panel>
      {error ? <ErrorState message={error} /> : null}
      <Panel title="Journey">
        {loading ? <LoadingState /> : null}
        {!loading && !data ? <EmptyState title="No timeline loaded" /> : null}
        {!loading && rows.length ? <DataTable rows={rows} /> : null}
        {!loading && summary ? (
          <div className="mt-4">
            <KeyValueList data={summary} />
          </div>
        ) : null}
      </Panel>
    </div>
  )
}