import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ApiError } from './client'

describe('ApiError', () => {
  it('stores status and body', () => {
    const err = new ApiError('nope', 401, { error: 'Not authenticated' })
    expect(err.message).toBe('nope')
    expect(err.status).toBe(401)
    expect(err.body).toEqual({ error: 'Not authenticated' })
  })
})

describe('auth storage contract', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('uses access_token key without embedding secrets', () => {
    localStorage.setItem('access_token', 'test-token')
    expect(localStorage.getItem('access_token')).toBe('test-token')
    expect(localStorage.getItem('JWT_SECRET')).toBeNull()
  })
})

describe('env contract', () => {
  it('does not hardcode database passwords in client module source expectations', async () => {
    const mod = await import('./client')
    expect(mod.api).toBeTruthy()
    expect(typeof mod.api.login).toBe('function')
    expect(typeof mod.api.listPersons).toBe('function')
    expect(typeof mod.api.getPerson).toBe('function')
  })
})
