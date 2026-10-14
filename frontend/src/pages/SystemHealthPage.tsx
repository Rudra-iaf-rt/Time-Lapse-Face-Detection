import { useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import type { ReadyStatus } from '@/types'
import { PageHeader, Panel, LoadingState, ErrorState, KeyValueList, StatCard } from '@/components/ui'

export function SystemHealthPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [ready, setReady] = useState<ReadyStatus | null>(null)
  const [live, setLive] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const [h, l] = await Promise.all([api.health(), api.live()])
        setHealth(h as Record<string, unknown>)
        setLive(l as Record<string, unknown>)
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

  const readyDependencies = ready?.dependencies

  return (
    <div>
      <PageHeader title="System Health" subtitle="/health, /live, and /ready probes." />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard label="Overall" value={ready?.status ?? 'unknown'} tone={ready?.status === 'ready' ? 'ok' : 'warn'} />
        <StatCard label="PostgreSQL" value={readyDependencies?.postgresql ?? 'unknown'} />
        <StatCard label="Redis" value={readyDependencies?.redis ?? 'unknown'} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Panel title="/live">
          <KeyValueList data={live} />
        </Panel>
        <Panel title="/health">
          <KeyValueList data={health} />
        </Panel>
        <Panel title="/ready">
          <KeyValueList data={(ready as unknown as Record<string, unknown>) || null} />
        </Panel>
      </div>
    </div>
  )
}