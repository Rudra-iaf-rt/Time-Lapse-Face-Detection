import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { TopologyData } from '@/types'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, StatCard } from '@/components/ui'

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

  const edges = Array.isArray(data?.edges) ? data.edges : []
  const edgeRows = edges.map((edge) => ({
    from_camera: edge.from_camera,
    to_camera: edge.to_camera,
    label: edge.label || `${edge.from_camera} to ${edge.to_camera}`,
    transition_probability: edge.transition_probability,
    ...Object.fromEntries(Object.entries(edge).filter(([key]) => !['from_camera', 'to_camera', 'label', 'transition_probability'].includes(key))),
  }))

  return (
    <div>
      <PageHeader
        title="Camera Topology"
        subtitle="Edges come from backend CameraGraph. Relationships are not invented in the UI."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard label="Nodes" value={data?.nodes?.length ?? 0} />
        <StatCard label="Edges" value={edges.length} />
        <StatCard label="Recorded transitions" value={data?.edge_count ?? 0} />
      </div>
      <Panel title="Camera nodes">
        {!loading && !(data?.nodes?.length) ? (
          <EmptyState title="No nodes" detail="Camera nodes appear when the graph has observations." />
        ) : (
          <div className="flex flex-wrap gap-2">
            {(data?.nodes || []).map((node, idx) => (
              <span
                key={`${String(node)}-${idx}`}
                className="rounded-full border border-[var(--line)] bg-[var(--bg-elevated)] px-3 py-1 text-sm font-medium"
              >
                {String(node)}
              </span>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Transitions" className="mt-4">
        {!loading && edgeRows.length === 0 ? (
          <EmptyState
            title="No topology edges"
            detail="When the transition learner has observations, edges such as 0 to 1 appear here."
          />
        ) : (
          <DataTable rows={edgeRows} />
        )}
      </Panel>
    </div>
  )
}