import { createContext, useContext, useMemo, useState, useCallback, type ReactNode } from 'react'
import type { AuthToken, Role } from '@/types'
import { api } from '@/api/client'

interface AuthState {
  token: string | null
  username: string | null
  role: Role | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthState | null>(null)

function readStored(): Pick<AuthToken, 'access_token' | 'username' | 'role'> | null {
  const token = localStorage.getItem('access_token')
  const username = localStorage.getItem('username')
  const role = localStorage.getItem('role') as Role | null
  if (!token || !username || !role) return null
  return { access_token: token, username, role }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = readStored()
  const [token, setToken] = useState<string | null>(stored?.access_token ?? null)
  const [username, setUsername] = useState<string | null>(stored?.username ?? null)
  const [role, setRole] = useState<Role | null>(stored?.role ?? null)

  const login = useCallback(async (user: string, password: string) => {
    const res = await api.login(user, password)
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('username', res.username)
    localStorage.setItem('role', res.role)
    setToken(res.access_token)
    setUsername(res.username)
    setRole(res.role)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    setToken(null)
    setUsername(null)
    setRole(null)
  }, [])

  const value = useMemo(
    () => ({
      token,
      username,
      role,
      login,
      logout,
      isAuthenticated: Boolean(token),
    }),
    [token, username, role, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
