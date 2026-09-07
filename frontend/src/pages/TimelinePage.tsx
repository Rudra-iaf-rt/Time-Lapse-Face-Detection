import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

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
    // Prefill from first person if available
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

  return (
    <div>
      <PageHeader title="Timeline" subtitle="Camera journey and sightings for a global_id." />
      <Panel className="mb-4">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void load(globalId)
          }}
        >
          <input
            className="rounded-lg border px-3 py-2 text-sm flex-1"
            value={globalId}
            onChange={(e) => setGlobalId(e.target.value)}
            placeholder="PERSON_0007"
          />
          <button type="submit" className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white">
            Load
          </button>
        </form>
      </Panel>
      {error ? <ErrorState message={error} /> : null}
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && !data ? <EmptyState title="No timeline loaded" /> : null}
        {data ? (
          <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-[32rem]">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : null}
      </Panel>
    </div>
  )
}
