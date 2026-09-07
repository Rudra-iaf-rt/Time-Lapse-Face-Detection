import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { PersonRow } from '@/types'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState } from '@/components/ui'

export function PersonsPage() {
  const [items, setItems] = useState<PersonRow[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load(q?: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await api.listPersons(1, 50, q)
      setItems(res.data?.items || [])
      setTotal(res.data?.total || 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load persons')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div>
      <PageHeader
        title="Persons"
        subtitle="Canonical identifier is global_id (e.g. PERSON_0007)."
        actions={
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              void load(search.trim() || undefined)
            }}
          >
            <input
              className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm"
              placeholder="Filter global_id"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit" className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white">
              Search
            </button>
          </form>
        }
      />
      {error ? <ErrorState message={error} /> : null}
      <Panel>
        {loading ? <LoadingState /> : null}
        {!loading && items.length === 0 ? (
          <EmptyState title="No persons found" detail="Pipeline output populates IdentityStore." />
        ) : (
          <>
            <div className="text-sm text-[var(--ink-muted)] mb-3">{total} identities</div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--ink-muted)] border-b border-[var(--line)]">
                  <th className="py-2">global_id</th>
                  <th>Status</th>
                  <th>Last camera</th>
                  <th>Last seen</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.global_id} className="border-b border-[var(--line)]/60">
                    <td className="py-2 font-medium">{p.global_id}</td>
                    <td>{p.status || '—'}</td>
                    <td>{String(p.last_camera ?? '—')}</td>
                    <td>{String(p.last_seen ?? '—')}</td>
                    <td className="text-right">
                      <Link to={`/persons/${p.global_id}`} className="text-[var(--accent)] underline">
                        Detail
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Panel>
    </div>
  )
}
