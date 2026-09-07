import { useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState } from '@/components/ui'
import type { ReadyStatus } from '@/types'

export function SystemHealthPage() {
  const [health, setHealth] = useState<unknown>(null)
  const [ready, setReady] = useState<ReadyStatus | null>(null)
  const [live, setLive] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const [h, l] = await Promise.all([api.health(), api.live()])
        setHealth(h)
        setLive(l)
        try {
          setReady(await api.ready())
        } catch (e) {
          if (e instanceof ApiError && e.body && typeof e.body === 'object') {
            setReady(e.body as ReadyStatus)
          } else {
            throw e
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Health check failed')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <div>
      <PageHeader title="System Health" subtitle="/health, /live, and /ready probes." />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <Panel>
          <h3 className="font-medium mb-2">/live</h3>
          <pre className="text-xs">{JSON.stringify(live, null, 2)}</pre>
        </Panel>
        <Panel>
          <h3 className="font-medium mb-2">/health</h3>
          <pre className="text-xs overflow-auto">{JSON.stringify(health, null, 2)}</pre>
        </Panel>
        <Panel>
          <h3 className="font-medium mb-2">/ready</h3>
          <pre className="text-xs overflow-auto">{JSON.stringify(ready, null, 2)}</pre>
        </Panel>
      </div>
    </div>
  )
}
