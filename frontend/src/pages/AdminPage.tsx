import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { useAuth } from '@/store/auth'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, KeyValueList } from '@/components/ui'

export function AdminPage() {
  const { role } = useAuth()
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [stats, setStats] = useState<Record<string, unknown> | null>(null)
  const [models, setModels] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.adminHealth().catch((e) => ({ error: e instanceof Error ? e.message : 'Admin health unavailable' })),
      api.identityStats().catch((e) => ({ error: e instanceof Error ? e.message : 'Identity stats unavailable' })),
      api.modelStatus().catch((e) => ({ error: e instanceof Error ? e.message : 'Model status unavailable' })),
    ])
      .then(([d, s, m]) => {
        setDetail(('data' in d ? (d.data as Record<string, unknown>) : (d as Record<string, unknown>)) || null)
        setStats(('data' in s ? (s.data as Record<string, unknown>) : (s as Record<string, unknown>)) || null)
        setModels(('data' in m ? (m.data as Record<string, unknown>) : (m as Record<string, unknown>)) || null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Admin endpoints failed'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader
        title="Admin"
        subtitle={`Signed in as ${role}. Admin health detail requires ADMIN role.`}
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Health detail">
          {detail ? <KeyValueList data={detail} /> : <EmptyState title="No admin health payload" />}
        </Panel>
        <Panel title="IdentityStore stats">
          {stats ? <KeyValueList data={stats} /> : <EmptyState title="No stats" />}
        </Panel>
        <Panel title="Model status">
          {models ? <KeyValueList data={models} /> : <EmptyState title="No model status" />}
        </Panel>
      </div>
    </div>
  )
}