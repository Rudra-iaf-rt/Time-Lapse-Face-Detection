import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { PageHeader, Panel, LoadingState, ErrorState, EmptyState, Toast } from '@/components/ui'

export function PersonDetailPage() {
  const { globalId = '' } = useParams()
  const [data, setData] = useState<unknown>(null)
  const [timeline, setTimeline] = useState<unknown>(null)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [person, tl] = await Promise.all([
        api.getPerson(globalId),
        api.personTimeline(globalId).catch(() => null),
      ])
      setData(person.data)
      setTimeline(tl?.data || null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load person')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (globalId) void load()
  }, [globalId])

  async function onNote(e: FormEvent) {
    e.preventDefault()
    if (!note.trim()) return
    if (!window.confirm('Add this note to the identity record?')) return
    try {
      await api.addNote(globalId, note.trim())
      setNote('')
      setToast('Note added')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Note failed')
    }
  }

  async function onResolve() {
    if (!window.confirm(`Resolve ${globalId}?`)) return
    try {
      await api.resolvePerson(globalId)
      setToast('Resolved')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Resolve failed')
    }
  }

  async function onReactivate() {
    if (!window.confirm(`Reactivate ${globalId}?`)) return
    try {
      await api.reactivatePerson(globalId)
      setToast('Reactivated')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reactivate failed')
    }
  }

  const identity = (data as { identity_store?: Record<string, unknown> } | null)?.identity_store

  return (
    <div>
      <PageHeader
        title={globalId}
        subtitle="Person detail — global_id is the permanent identity key."
        actions={
          <div className="flex gap-2">
            <button type="button" onClick={onResolve} className="rounded-lg border px-3 py-2 text-sm">
              Resolve
            </button>
            <button
              type="button"
              onClick={onReactivate}
              className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white"
            >
              Reactivate
            </button>
          </div>
        }
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <h3 className="font-medium mb-2">Identity</h3>
          {!identity ? (
            <EmptyState title="No IdentityStore record" />
          ) : (
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-[var(--ink-muted)]">Status</dt>
              <dd>{String(identity.status ?? '—')}</dd>
              <dt className="text-[var(--ink-muted)]">First seen</dt>
              <dd>{String(identity.first_seen ?? '—')}</dd>
              <dt className="text-[var(--ink-muted)]">Last seen</dt>
              <dd>{String(identity.last_seen ?? '—')}</dd>
              <dt className="text-[var(--ink-muted)]">Last camera</dt>
              <dd>{String(identity.last_camera ?? '—')}</dd>
              <dt className="text-[var(--ink-muted)]">Notes</dt>
              <dd className="whitespace-pre-wrap">{String(identity.notes ?? '—')}</dd>
            </dl>
          )}
        </Panel>

        <Panel>
          <h3 className="font-medium mb-2">Add note</h3>
          <form onSubmit={onNote} className="space-y-2">
            <textarea
              className="w-full rounded-lg border border-[var(--line)] p-2 text-sm"
              rows={4}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Operator note"
            />
            <button type="submit" className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white">
              Save note
            </button>
          </form>
        </Panel>

        <Panel className="lg:col-span-2">
          <h3 className="font-medium mb-2">Timeline / journey</h3>
          {timeline ? (
            <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-96">
              {JSON.stringify(timeline, null, 2)}
            </pre>
          ) : (
            <EmptyState title="No timeline data from backend" />
          )}
        </Panel>

        <Panel className="lg:col-span-2">
          <h3 className="font-medium mb-2">Raw response</h3>
          <pre className="text-xs overflow-auto bg-[var(--bg-elevated)] p-3 rounded-lg max-h-64">
            {JSON.stringify(data, null, 2)}
          </pre>
        </Panel>
      </div>
      <Toast message={toast} />
    </div>
  )
}
