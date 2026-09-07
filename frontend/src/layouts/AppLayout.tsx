import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/store/auth'
import { useEffect, useState } from 'react'
import { api } from '@/api/client'

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/live', label: 'Live Monitoring' },
  { to: '/persons', label: 'Persons' },
  { to: '/timeline', label: 'Timeline' },
  { to: '/search', label: 'Search' },
  { to: '/cameras', label: 'Cameras' },
  { to: '/topology', label: 'Camera Topology' },
  { to: '/behavior', label: 'Behavior' },
  { to: '/anomalies', label: 'Anomalies' },
  { to: '/crowd', label: 'Crowd Analytics' },
  { to: '/health', label: 'System Health' },
  { to: '/admin', label: 'Admin' },
]

export function AppLayout() {
  const { username, role, logout } = useAuth()
  const [ready, setReady] = useState<string>('checking')

  useEffect(() => {
    api
      .ready()
      .then((r) => setReady(r.status))
      .catch(() => setReady('unreachable'))
  }, [])

  return (
    <div className="min-h-screen grid grid-cols-[240px_1fr]">
      <aside className="bg-[var(--sidebar)] text-[var(--sidebar-ink)] px-4 py-6 flex flex-col gap-6">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Operator</div>
          <h1 className="text-xl font-semibold mt-1 leading-tight">MultiCam Re-ID</h1>
        </div>
        <nav className="flex flex-col gap-1 text-sm">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 transition ${
                  isActive ? 'bg-teal-800/60 text-white' : 'hover:bg-white/5'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto text-xs text-slate-400 space-y-1">
          <div>{username}</div>
          <div>{role}</div>
          <button
            type="button"
            onClick={logout}
            className="mt-2 text-teal-200 hover:text-white underline"
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex flex-col">
        <header className="h-14 border-b border-[var(--line)] bg-[var(--surface)]/80 backdrop-blur px-6 flex items-center justify-between">
          <div className="text-sm text-[var(--ink-muted)]">Identity key: global_id</div>
          <div className="flex items-center gap-3 text-sm">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 ${
                ready === 'ready'
                  ? 'bg-emerald-50 text-emerald-800'
                  : 'bg-amber-50 text-amber-800'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  ready === 'ready' ? 'bg-emerald-600' : 'bg-amber-500'
                }`}
              />
              API {ready}
            </span>
          </div>
        </header>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
