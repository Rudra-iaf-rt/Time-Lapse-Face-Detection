import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

export function CamerasPage() {
  const [cameras, setCameras] = useState<unknown[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .listCameras()
      .then((r) => setCameras((r.data as unknown[]) || []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load cameras'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader title="Cameras" subtitle="Camera list and metadata from the API." />
      {error ? <ErrorState message={error} /> : null}
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && cameras.length === 0 ? (
          <EmptyState title="No cameras registered" detail="PostgreSQL camera rows or SQLite-derived IDs appear here." />
        ) : (
          <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg">
            {JSON.stringify(cameras, null, 2)}
          </pre>
        )}
      </Panel>
    </div>
  )
}
