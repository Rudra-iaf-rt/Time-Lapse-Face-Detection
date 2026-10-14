import { useEffect, useState, type FormEvent } from 'react'
import { api } from '@/api/client'
import { useAuth } from '@/store/auth'
import {
  PageHeader,
  Panel,
  LoadingState,
  ErrorState,
  EmptyState,
  DataTable,
  StatCard,
  KeyValueList,
} from '@/components/ui'

interface CameraRow extends Record<string, unknown> {
  camera_id: number | string
  name?: string
  source_uri?: string
  status?: string
  metadata?: Record<string, unknown>
}

export function CamerasPage() {
  const { role } = useAuth()
  const canManage = role === 'ADMIN' || role === 'OPERATOR'
  const [cameras, setCameras] = useState<CameraRow[]>([])
  const [runtimeRows, setRuntimeRows] = useState<Array<Record<string, unknown>>>([])
  const [selectedRuntimeCamera, setSelectedRuntimeCamera] = useState('1')
  const [runtimeSource, setRuntimeSource] = useState('')
  const [runtimeBusy, setRuntimeBusy] = useState(false)
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [registering, setRegistering] = useState(false)
  const [testing, setTesting] = useState(false)

  const [form, setForm] = useState({
    camera_id: '1',
    name: 'Camera 1',
    location: '',
    source_type: 'file',
    source_uri: '',
    capacity: '100',
  })

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.listCameras()
      setCameras((res.data as CameraRow[]) || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load cameras')
    } finally {
      setLoading(false)
    }
  }

  async function loadRuntime() {
    try {
      const res = await api.listCameraRuntime()
      setRuntimeRows((res.data as Array<Record<string, unknown>>) || [])
    } catch {
      setRuntimeRows([])
    }
  }

  useEffect(() => {
    void load()
    void loadRuntime()
    const cameraTimer = window.setInterval(() => void load(), 10000)
    const runtimeTimer = window.setInterval(() => void loadRuntime(), 2000)
    return () => {
      window.clearInterval(cameraTimer)
      window.clearInterval(runtimeTimer)
    }
  }, [])

  async function onTest(e?: FormEvent) {
    e?.preventDefault()
    if (!form.source_uri.trim()) {
      setError('Enter a source URI before testing')
      return
    }
    setTesting(true)
    setError(null)
    try {
      const res = await api.testCamera(form.source_uri.trim(), 5)
      setTestResult((res.data as Record<string, unknown>) || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Camera test failed')
      setTestResult(null)
    } finally {
      setTesting(false)
    }
  }

  async function startRuntime(cameraId: string, source?: string) {
    setRuntimeBusy(true)
    setError(null)
    try {
      await api.startCamera(cameraId, source || runtimeSource || undefined)
      await loadRuntime()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start camera runtime')
    } finally {
      setRuntimeBusy(false)
    }
  }

  async function stopRuntime(cameraId: string) {
    setRuntimeBusy(true)
    setError(null)
    try {
      await api.stopCamera(cameraId)
      await loadRuntime()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop camera runtime')
    } finally {
      setRuntimeBusy(false)
    }
  }

  async function onRegister(e: FormEvent) {
    e.preventDefault()
    setRegistering(true)
    setError(null)
    try {
      await api.createCamera({
        camera_id: Number(form.camera_id),
        name: form.name.trim() || `Camera ${form.camera_id}`,
        location: form.location.trim() || null,
        capacity: Number(form.capacity || 100),
        source_type: form.source_type,
        source_uri: form.source_uri.trim() || null,
        metadata: {
          source_type: form.source_type,
          source_uri: form.source_uri.trim() || null,
        },
      })
      await load()
      setTestResult(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Camera registration failed')
    } finally {
      setRegistering(false)
    }
  }

  const rows = cameras.map((camera) => ({
    ...camera,
    source: (camera.metadata as Record<string, unknown> | undefined)?.source_uri || camera.source_uri || camera.source_type,
  }))

  return (
    <div>
      <PageHeader
        title="Cameras"
        subtitle="Register, test, and manage camera sources. Webcam index 0, RTSP, HTTP, and file paths are supported."
      />
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        <StatCard label="Registered cameras" value={cameras.length} />
        <StatCard label="Last test" value={testResult ? 'completed' : 'not run'} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Add camera">
          <form onSubmit={onRegister} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                Camera ID
                <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={form.camera_id} onChange={(e) => setForm((p) => ({ ...p, camera_id: e.target.value }))} />
              </label>
              <label className="text-sm">
                Capacity
                <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={form.capacity} onChange={(e) => setForm((p) => ({ ...p, capacity: e.target.value }))} />
              </label>
            </div>
            <label className="text-sm">
              Name
              <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
            </label>
            <label className="text-sm">
              Location
              <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={form.location} onChange={(e) => setForm((p) => ({ ...p, location: e.target.value }))} />
            </label>
            <label className="text-sm">
              Source type
              <select className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={form.source_type} onChange={(e) => setForm((p) => ({ ...p, source_type: e.target.value }))}>
                <option value="file">File</option>
                <option value="webcam">Webcam</option>
                <option value="rtsp">RTSP</option>
                <option value="http">HTTP/MJPEG</option>
              </select>
            </label>
            <label className="text-sm">
              Source URI
              <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" placeholder="0, rtsp://..., or /path/to/video.mp4" value={form.source_uri} onChange={(e) => setForm((p) => ({ ...p, source_uri: e.target.value }))} />
            </label>
            <div className="flex gap-2">
              <button type="button" disabled={testing || !canManage} onClick={() => void onTest()} className="rounded-lg border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50">
                {testing ? 'Testing...' : 'Test connection'}
              </button>
              <button type="submit" disabled={registering || !canManage} className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white disabled:opacity-50">
                {registering ? 'Registering...' : 'Register camera'}
              </button>
            </div>
          </form>
        </Panel>

        <Panel title="Connection test result">
          {!testResult ? <EmptyState title="No test run" detail="Use Test connection to validate a source before saving it." /> : <KeyValueList data={testResult} />}
        </Panel>
      </div>

      <Panel title="Live runtime control" className="mt-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            Camera ID
            <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" value={selectedRuntimeCamera} onChange={(e) => setSelectedRuntimeCamera(e.target.value)} />
          </label>
          <label className="text-sm sm:col-span-2">
            Source URI for runtime
            <input className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2" placeholder="Use registered camera source or enter one here" value={runtimeSource} onChange={(e) => setRuntimeSource(e.target.value)} />
          </label>
        </div>
        <div className="mt-3 flex gap-2">
          <button type="button" disabled={runtimeBusy || !canManage} onClick={() => void startRuntime(selectedRuntimeCamera, runtimeSource)} className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white disabled:opacity-50">
            Start runtime
          </button>
          <button type="button" disabled={runtimeBusy || !canManage} onClick={() => void stopRuntime(selectedRuntimeCamera)} className="rounded-lg border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50">
            Stop runtime
          </button>
        </div>
        <div className="mt-4">
          {runtimeRows.length ? (
            <DataTable
              rows={runtimeRows.map((row) => ({
                ...row,
                identified_persons: Array.isArray(row.last_global_ids) ? row.last_global_ids.join(', ') : '—',
              }))}
              columns={['camera_id', 'running', 'frames_read', 'fps', 'width', 'height', 'identified_persons', 'error']}
            />
          ) : (
            <EmptyState title="No camera runtimes" detail="Start a camera runtime to see live frame counts and status." />
          )}
        </div>
      </Panel>

      <Panel title="Camera inventory" className="mt-4">
        {!loading && rows.length === 0 ? <EmptyState title="No cameras registered" detail="PostgreSQL stores registered cameras. SQLite-derived IDs appear when PostgreSQL is unavailable." /> : null}
        {!loading && rows.length ? <DataTable rows={rows} columns={['camera_id', 'name', 'location', 'source', 'capacity']} /> : null}
      </Panel>
    </div>
  )
}