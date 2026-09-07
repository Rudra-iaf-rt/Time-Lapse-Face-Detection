import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { useAuth } from '@/store/auth'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

export function AdminPage() {
  const { role } = useAuth()
  const [detail, setDetail] = useState<unknown>(null)
  const [stats, setStats] = useState<unknown>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.adminHealth().catch((e) => ({ error: e.message })),
      api.identityStats().catch((e) => ({ error: e.message })),
    ])
      .then(([d, s]) => {
        setDetail('data' in d ? d.data : d)
        setStats('data' in s ? s.data : s)
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
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <h3 className="font-medium mb-2">Health detail</h3>
          {detail ? (
            <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-96">
              {JSON.stringify(detail, null, 2)}
            </pre>
          ) : (
            <EmptyState title="No admin health payload" />
          )}
        </Panel>
        <Panel>
          <h3 className="font-medium mb-2">IdentityStore stats</h3>
          {stats ? (
            <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-96">
              {JSON.stringify(stats, null, 2)}
            </pre>
          ) : (
            <EmptyState title="No stats" />
          )}
        </Panel>
      </div>
    </div>
  )
}
