import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, StatCard } from '@/components/ui'

export function CamerasPage() {
  const [cameras, setCameras] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .listCameras()
      .then((r) => setCameras((r.data as Array<Record<string, unknown>>) || []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load cameras'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader title="Cameras" subtitle="Camera list and metadata from the API." />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard label="Registered cameras" value={cameras.length} />
      </div>
      <Panel title="Camera inventory">
        {!loading && cameras.length === 0 ? (
          <EmptyState title="No cameras registered" detail="PostgreSQL camera rows or SQLite-derived IDs appear here." />
        ) : (
          <DataTable rows={cameras} emptyTitle="No cameras registered" />
        )}
      </Panel>
    </div>
  )
}