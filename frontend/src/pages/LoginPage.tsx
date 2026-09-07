import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/store/auth'
import { ApiError } from '@/api/client'

export function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) return <Navigate to="/" replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-8 shadow-sm"
      >
        <div className="text-xs uppercase tracking-[0.22em] text-[var(--accent)]">MultiCam Re-ID</div>
        <h1 className="mt-2 text-3xl font-semibold">Operator sign-in</h1>
        <p className="mt-2 text-sm text-[var(--ink-muted)]">
          Authenticate against the FastAPI JWT service. Credentials come from environment
          configuration — never hardcoded in the UI.
        </p>
        <label className="mt-6 block text-sm">
          Username
          <input
            className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="mt-4 block text-sm">
          Password
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-[var(--line)] px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="mt-6 w-full rounded-lg bg-[var(--accent)] px-4 py-2.5 text-white disabled:opacity-60"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
