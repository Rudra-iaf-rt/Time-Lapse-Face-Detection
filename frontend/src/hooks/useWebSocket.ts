import { useCallback, useEffect, useRef, useState } from 'react'
import type { WsEvent } from '@/types'

export type WsStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

export function useWebSocket(clientId: string, enabled = true) {
  const [status, setStatus] = useState<WsStatus>('idle')
  const [events, setEvents] = useState<WsEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const timerRef = useRef<number | null>(null)

  const disconnect = useCallback(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current)
    wsRef.current?.close()
    wsRef.current = null
    setStatus('closed')
  }, [])

  const connect = useCallback(() => {
    const base = import.meta.env.VITE_WS_URL as string | undefined
    if (!base) {
      setError('VITE_WS_URL is not configured')
      setStatus('error')
      return
    }
    const url = `${base.replace(/\/$/, '')}/${encodeURIComponent(clientId)}`
    setStatus('connecting')
    setError(null)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      retryRef.current = 0
      setStatus('open')
      ws.send(JSON.stringify({ action: 'subscribe', topics: ['all'] }))
    }

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as WsEvent
        setEvents((prev) => [data, ...prev].slice(0, 100))
      } catch {
        setError('Received malformed WebSocket payload')
      }
    }

    ws.onerror = () => {
      setStatus('error')
      setError('WebSocket connection error')
    }

    ws.onclose = () => {
      setStatus('closed')
      const attempt = retryRef.current + 1
      retryRef.current = attempt
      const delay = Math.min(1000 * 2 ** attempt, 15000)
      timerRef.current = window.setTimeout(() => {
        if (enabled) connect()
      }, delay)
    }
  }, [clientId, enabled])

  useEffect(() => {
    if (!enabled) {
      disconnect()
      return
    }
    connect()
    return () => disconnect()
  }, [connect, disconnect, enabled])

  const send = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  return { status, events, error, send, reconnect: connect, disconnect }
}
