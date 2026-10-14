import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { PersonRow } from '@/types'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, DataTable, Pagination } from '@/components/ui'

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
            <DataTable
              rows={items as Array<Record<string, unknown>>}
              columns={['global_id', 'status', 'last_camera', 'last_seen', 'confidence']}
            />
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