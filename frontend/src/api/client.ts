import type { ApiEnvelope, AuthToken, PersonListData, ReadyStatus, TopologyData } from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE_URL as string | undefined

if (!API_BASE) {
  console.warn('VITE_API_BASE_URL is not set. Set it in frontend/.env')
}

function baseUrl(): string {
  const raw = API_BASE || ''
  return raw.replace(/\/$/, '')
}

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

function authHeader(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(init.headers || {})
  if (auth) {
    const a = authHeader()
    Object.entries(a).forEach(([k, v]) => headers.set(k, v as string))
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${baseUrl()}${path}`, { ...init, headers })
  const text = await res.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = text
  }

  if (!res.ok) {
    const msg =
      typeof body === 'object' && body && 'error' in body
        ? String((body as { error: string }).error)
        : `HTTP ${res.status}`
    throw new ApiError(msg, res.status, body)
  }
  return body as T
}

export const api = {
  health: () => request<Record<string, unknown>>('/health', {}, false),
  live: () => request<Record<string, unknown>>('/live', {}, false),
  ready: () => request<ReadyStatus>('/ready', {}, false),

  login: async (username: string, password: string) => {
    const form = new URLSearchParams()
    form.set('username', username)
    form.set('password', password)
    return request<AuthToken>(
      '/api/auth/login',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      },
      false,
    )
  },

  listPersons: (page = 1, perPage = 20, search?: string) => {
    const q = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    })
    if (search) q.set('search', search)
    return request<ApiEnvelope<PersonListData>>(`/api/persons?${q}`)
  },

  getPerson: (globalId: string) =>
    request<ApiEnvelope>(`/api/persons/${encodeURIComponent(globalId)}`),

  personTimeline: (globalId: string) =>
    request<ApiEnvelope>(`/api/persons/${encodeURIComponent(globalId)}/timeline`),

  addNote: (globalId: string, note: string) =>
    request<ApiEnvelope>(`/api/persons/${encodeURIComponent(globalId)}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  resolvePerson: (globalId: string) =>
    request<ApiEnvelope>(`/api/persons/${encodeURIComponent(globalId)}/resolve`, {
      method: 'POST',
    }),

  reactivatePerson: (globalId: string) =>
    request<ApiEnvelope>(`/api/persons/${encodeURIComponent(globalId)}/reactivate`, {
      method: 'POST',
    }),

  searchPersons: (params: Record<string, string | undefined>) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v) q.set(k, v)
    })
    return request<ApiEnvelope>(`/api/search/persons?${q}`)
  },

  listCameras: () => request<ApiEnvelope>(`/api/cameras`),
  cameraTopology: () => request<ApiEnvelope<TopologyData>>(`/api/cameras/topology/graph`),
  listTracks: (globalId?: string) => {
    const q = globalId ? `?global_id=${encodeURIComponent(globalId)}` : ''
    return request<ApiEnvelope>(`/api/tracks${q}`)
  },
  analyticsSummary: () => request<ApiEnvelope>(`/api/analytics/summary`),
  occupancy: (cameraId?: number) => {
    const q = cameraId != null ? `?camera_id=${cameraId}` : ''
    return request<ApiEnvelope>(`/api/analytics/occupancy${q}`)
  },
  anomalies: () => request<ApiEnvelope>(`/api/analytics/anomalies`),
  dwell: (globalId?: string) => {
    const q = globalId ? `?global_id=${encodeURIComponent(globalId)}` : ''
    return request<ApiEnvelope>(`/api/analytics/dwell${q}`)
  },
  entryExit: () => request<ApiEnvelope>(`/api/analytics/entry-exit`),
  adminHealth: () => request<ApiEnvelope>(`/api/admin/health-detail`),
  identityStats: () => request<ApiEnvelope>(`/api/admin/identity-stats`),
  wsStatus: () => request<Record<string, unknown>>(`/api/websocket/status`),
}
