import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

export function CrowdPage() {
  const [occupancy, setOccupancy] = useState<unknown[]>([])
  const [entryExit, setEntryExit] = useState<unknown[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.occupancy(), api.entryExit()])
      .then(([o, e]) => {
        setOccupancy((o.data as unknown[]) || [])
        setEntryExit((e.data as unknown[]) || [])
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Crowd analytics unavailable'))
      .finally(() => setLoading(false))
  }, [])

  const hasCharts = occupancy.length > 0 || entryExit.length > 0

  return (
    <div>
      <PageHeader
        title="Crowd Analytics"
        subtitle="Charts render only when the backend provides occupancy/entry-exit series."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      {!loading && !hasCharts ? (
        <Panel>
          <EmptyState
            title="No crowd metrics yet"
            detail="Occupancy, capacity, entry/exit rates appear after crowd modules write CrowdMetric rows."
          />
        </Panel>
      ) : null}
      {hasCharts ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel>
            <h3 className="font-medium mb-2">Occupancy</h3>
            <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-80">
              {JSON.stringify(occupancy, null, 2)}
            </pre>
          </Panel>
          <Panel>
            <h3 className="font-medium mb-2">Entry / exit</h3>
            <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-80">
              {JSON.stringify(entryExit, null, 2)}
            </pre>
          </Panel>
        </div>
      ) : null}
    </div>
  )
}
