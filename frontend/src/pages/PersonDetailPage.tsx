import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/api/client'
import {
  PageHeader,
  Panel,
  LoadingState,
  ErrorState,
  EmptyState,
  Toast,
  KeyValueList,
  DataTable,
} from '@/components/ui'

export function PersonDetailPage() {
  const { globalId = '' } = useParams()
  const [data, setData] = useState<unknown>(null)
  const [timeline, setTimeline] = useState<Record<string, unknown> | null>(null)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  async function load() {
    if (!globalId) return
    setLoading(true)
    setError(null)
    try {
      const [person, tl] = await Promise.all([
        api.getPerson(globalId),
        api.personTimeline(globalId).catch(() => null),
      ])
      setData(person.data)
      setTimeline((tl?.data as Record<string, unknown>) || null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load person')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
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

  const envelope = data as { identity_store?: Record<string, unknown>; [key: string]: unknown } | null
  const identity = envelope?.identity_store
  const timelineEvents = Array.isArray(timeline?.events)
    ? (timeline.events as Array<Record<string, unknown>>)
    : Array.isArray(timeline?.sqlite_events)
      ? (timeline.sqlite_events as Array<Record<string, unknown>>)
      : []
  const sightings = Array.isArray(timeline?.sightings)
    ? (timeline.sightings as Array<Record<string, unknown>>)
    : []

  return (
    <div>
      <PageHeader
        title={globalId}
        subtitle="Person detail. global_id is the permanent identity key."
        actions={
          <div className="flex gap-2">
            <button type="button" onClick={onResolve} className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
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
        <Panel title="Identity">
          {identity ? (
            <KeyValueList data={identity} />
          ) : (
            <EmptyState title="No IdentityStore record" detail="The API did not return identity_store data." />
          )}
        </Panel>

        <Panel title="Add note">
          <form onSubmit={onNote} className="space-y-3">
            <textarea
              className="w-full rounded-lg border border-[var(--line)] p-3 text-sm"
              rows={5}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Operator note"
            />
            <button type="submit" className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white">
              Save note
            </button>
          </form>
        </Panel>

        <Panel title="Timeline" className="lg:col-span-2">
          {timelineEvents.length ? (
            <DataTable rows={timelineEvents} />
          ) : (
            <EmptyState title="No timeline events" detail="No events were returned by the backend." />
          )}
        </Panel>

        {sightings.length ? (
          <Panel title="Sightings" className="lg:col-span-2">
            <DataTable rows={sightings} />
          </Panel>
        ) : null}

        <Panel title="Raw response" className="lg:col-span-2">
          <pre className="max-h-96 overflow-auto rounded-lg bg-[var(--bg-elevated)] p-3 text-xs">
            {JSON.stringify(data, null, 2)}
          </pre>
        </Panel>
      </div>
      <Toast message={toast} />
    </div>
  )
}