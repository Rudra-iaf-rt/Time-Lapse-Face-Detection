import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { TopologyData } from '@/types'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

export function TopologyPage() {
  const [data, setData] = useState<TopologyData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .cameraTopology()
      .then((r) => setData(r.data || null))
      .catch((e) => setError(e instanceof Error ? e.message : 'Topology unavailable'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader
        title="Camera Topology"
        subtitle="Edges come from backend CameraGraph — relationships are not invented in the UI."
      />
      {error ? <ErrorState message={error} /> : null}
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && (!data || data.edge_count === 0) ? (
          <EmptyState
            title="No topology edges"
            detail="When the transition learner has observations, edges such as CAM01 → CAM02 appear here."
          />
        ) : null}
        {data && data.edges?.length ? (
          <ul className="space-y-2">
            {data.edges.map((e, i) => (
              <li key={i} className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
                <span className="font-medium">
                  {e.label || `${e.from_camera} → ${e.to_camera}`}
                </span>
                {e.transition_probability != null ? (
                  <span className="ml-2 text-[var(--ink-muted)]">
                    p={e.transition_probability.toFixed(2)}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        {data ? (
          <pre className="mt-4 text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-64">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : null}
      </Panel>
    </div>
  )
}
