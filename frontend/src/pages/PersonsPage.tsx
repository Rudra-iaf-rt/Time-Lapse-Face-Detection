import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { PersonRow } from '@/types'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, Pagination, PersonImage } from '@/components/ui'

export function PersonsPage() {
  const [items, setItems] = useState<PersonRow[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const perPage = 20
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (nextPage = page, nextQuery = query) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.listPersons(nextPage, perPage, nextQuery.trim() || undefined)
      setItems(res.data?.items || [])
      setTotal(res.data?.total || 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load persons')
    } finally {
      setLoading(false)
    }
  }, [page, query])

  useEffect(() => {
    void load(page, query)
  }, [page, query, load])

  return (
    <div>
      <PageHeader
        title="Persons"
        subtitle="Canonical identifier is global_id. Filter, browse, and manage identities."
        actions={
          <form
            className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault()
              setPage(1)
              setQuery(search.trim())
            }}
          >
            <input
              className="w-full rounded-lg border border-[var(--line)] px-3 py-2 text-sm sm:w-64"
              placeholder="Filter global_id"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit" className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white">
              Search
            </button>
          </form>
        }
      />
      {error ? <ErrorState message={error} /> : null}
      <Panel title="Identity records">
        {loading ? <LoadingState label="Loading persons…" /> : null}
        {!loading && items.length === 0 ? (
          <EmptyState title="No persons found" detail="Pipeline output populates IdentityStore." />
        ) : (
          <>
            <div className="mb-3 text-sm text-[var(--ink-muted)]">
              Showing {items.length} of {total.toLocaleString()} identities
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-max text-sm">
                <thead>
                  <tr className="text-left text-[var(--ink-muted)]">
                    <th className="border-b border-[var(--line)] px-3 py-2">Image</th>
                    <th className="border-b border-[var(--line)] px-3 py-2">global_id</th>
                    <th className="border-b border-[var(--line)] px-3 py-2">Status</th>
                    <th className="border-b border-[var(--line)] px-3 py-2">Last camera</th>
                    <th className="border-b border-[var(--line)] px-3 py-2">Last seen</th>
                    <th className="border-b border-[var(--line)] px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.global_id} className="border-b border-[var(--line)]/60 hover:bg-[var(--bg-elevated)]/60">
                      <td className="px-3 py-2">
                        <PersonImage src={p.best_crop_url} alt={p.global_id} className="h-12 w-12" />
                      </td>
                      <td className="px-3 py-2 font-medium">{p.global_id}</td>
                      <td className="px-3 py-2">{p.status || '—'}</td>
                      <td className="px-3 py-2">{String(p.last_camera ?? '—')}</td>
                      <td className="px-3 py-2">{String(p.last_seen ?? '—')}</td>
                      <td className="px-3 py-2 text-right">
                        <Link to={`/persons/${p.global_id}`} className="text-[var(--accent)] underline">
                          Detail
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} perPage={perPage} total={total} onChange={setPage} />
          </>
        )}
      </Panel>
      <div className="mt-4">
        <Link to="/search" className="text-sm text-[var(--accent)] underline">
          Advanced search
        </Link>
      </div>
    </div>
  )
}