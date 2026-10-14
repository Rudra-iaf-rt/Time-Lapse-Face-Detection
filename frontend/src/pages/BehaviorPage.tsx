import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, KeyValueList } from '@/components/ui'

export function BehaviorPage() {
  const [data, setData] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .dwell()
      .then((r) => setData(r.data))
      .catch((e) => setError(e instanceof Error ? e.message : 'Behavior data unavailable'))
      .finally(() => setLoading(false))
  }, [])

  const rows = Array.isArray(data) ? (data as Array<Record<string, unknown>>) : []
  const summary = !Array.isArray(data) && data && typeof data === 'object' ? (data as Record<string, unknown>) : null

  return (
    <div>
      <PageHeader
        title="Behavior"
        subtitle="Dwell and visit-duration indicators from backend APIs. These are indicators, not assertions of wrongdoing."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <Panel title="Behavior data">
        {!loading && !data ? <EmptyState title="No behavior data from backend" /> : null}
        {!loading && rows.length ? <DataTable rows={rows} /> : null}
        {!loading && summary ? <KeyValueList data={summary} /> : null}
        {!loading && data && !rows.length && !summary ? (
          <pre className="max-h-[32rem] overflow-auto rounded-lg bg-[var(--bg-elevated)] p-3 text-xs">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : null}
      </Panel>
    </div>
  )
}