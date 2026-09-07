export type Role = 'ADMIN' | 'OPERATOR' | 'VIEWER'

export interface AuthToken {
  access_token: string
  token_type: string
  role: Role
  username: string
}

export interface ApiEnvelope<T = unknown> {
  success: boolean
  message?: string | null
  data?: T
  timestamp?: string
}

export interface PersonRow {
  global_id: string
  status?: string
  first_seen?: number | string
  last_seen?: number | string
  last_camera?: string | number
  confidence?: number
  notes?: string
  [key: string]: unknown
}

export interface PersonListData {
  items: PersonRow[]
  total: number
  page: number
  per_page: number
  source?: string
}

export interface TopologyData {
  nodes: Array<string | number>
  edges: Array<{
    from_camera: string | number
    to_camera: string | number
    label?: string
    transition_probability?: number
  }>
  edge_count: number
}

export interface ReadyStatus {
  status: string
  dependencies: {
    postgresql: string
    qdrant: string
    redis: string
  }
  timestamp?: string
}

export interface WsEvent {
  event: string
  timestamp?: string
  global_id?: string
  camera_id?: string | number
  message?: string
  [key: string]: unknown
}
