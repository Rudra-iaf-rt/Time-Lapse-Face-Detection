import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, StatCard } from '@/components/ui'

export function CrowdPage() {
  const [occupancy, setOccupancy] = useState<Array<Record<string, unknown>>>([])
  const [entryExit, setEntryExit] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.occupancy(), api.entryExit()])
      .then(([o, e]) => {
        setOccupancy((o.data as Array<Record<string, unknown>>) || [])
        setEntryExit((e.data as Array<Record<string, unknown>>) || [])
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Crowd analytics unavailable'))
      .finally(() => setLoading(false))
  }, [])

  const hasCharts = occupancy.length > 0 || entryExit.length > 0

  return (
    <div>
      <PageHeader
        title="Crowd Analytics"
        subtitle="Charts render only when the backend provides occupancy and entry/exit series."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard label="Occupancy samples" value={occupancy.length} />
        <StatCard label="Entry/exit samples" value={entryExit.length} />
      </div>
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
          <Panel title="Occupancy">
            {occupancy.length ? (
              <>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={occupancy}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#c5d0db" />
                      <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} hide={occupancy.length > 12} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="occupancy" stroke="#0d6e6e" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <DataTable rows={occupancy} />
              </>
            ) : (
              <EmptyState title="No occupancy samples" />
            )}
          </Panel>
          <Panel title="Entry / exit">
            {entryExit.length ? (
              <>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={entryExit}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#c5d0db" />
                      <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} hide={entryExit.length > 12} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="entry_rate" stroke="#067647" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="exit_rate" stroke="#b42318" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <DataTable rows={entryExit} />
              </>
            ) : (
              <EmptyState title="No entry/exit samples" />
            )}
          </Panel>
        </div>
      ) : null}
    </div>
  )
}