import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

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

  return (
    <div>
      <PageHeader
        title="Behavior"
        subtitle="Possible unusual activity indicators from backend dwell/behavior APIs — not assertions of wrongdoing."
      />
      {error ? <ErrorState message={error} /> : null}
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && !data ? <EmptyState title="No behavior data from backend" /> : null}
        {data ? (
          <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-[32rem]">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : null}
      </Panel>
    </div>
  )
}
