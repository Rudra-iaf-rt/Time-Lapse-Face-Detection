import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, StatCard } from '@/components/ui'

export function AnomaliesPage() {
  const [data, setData] = useState<Array<Record<string, unknown>>>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .anomalies()
      .then((r) => {
        setData((r.data as Array<Record<string, unknown>>) || [])
        setMessage(r.message || null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Anomalies unavailable'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader
        title="Anomalies"
        subtitle="Possible unusual activity summaries from PostgreSQL anomaly records."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        <StatCard label="Anomaly records" value={data.length} />
      </div>
      <Panel title="Anomaly records">
        {!loading && data.length === 0 ? (
          <EmptyState title="No anomalies recorded" detail={message || 'Backend returned an empty anomaly list.'} />
        ) : (
          <DataTable rows={data} emptyTitle="No anomalies recorded" emptyDetail={message || undefined} />
        )}
      </Panel>
    </div>
  )
}