import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

export function AnomaliesPage() {
  const [data, setData] = useState<unknown[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .anomalies()
      .then((r) => {
        setData((r.data as unknown[]) || [])
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
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && data.length === 0 ? (
          <EmptyState
            title="No anomalies recorded"
            detail={message || 'Backend returned an empty anomaly list.'}
          />
        ) : (
          <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-[32rem]">
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
      </Panel>
    </div>
  )
}
