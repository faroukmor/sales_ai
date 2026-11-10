import { afterEach, describe, expect, it, vi } from 'vitest'
import { setCsrfToken, storeApi } from './api'

function mockFetch(response) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(response)
}

afterEach(() => vi.restoreAllMocks())

describe('storeApi request headers', () => {
  it('keeps Content-Type on write requests together with the CSRF token', async () => {
    const spy = mockFetch({ ok: true, status: 201, json: async () => ({ id: 1 }) })
    setCsrfToken('csrf-123')
    await storeApi.createAdminProduct({ name: 'TV', category: 'TV' })
    const [, options] = spy.mock.calls[0]
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(options.headers['X-CSRF-Token']).toBe('csrf-123')
    expect(options.credentials).toBe('include')
    expect(options.method).toBe('POST')
  })

  it('keeps Content-Type on read and login requests', async () => {
    const spy = mockFetch({ ok: true, status: 200, json: async () => ({}) })
    await storeApi.login({ email: 'a@b.com', password: 'x' })
    expect(spy.mock.calls[0][1].headers['Content-Type']).toBe('application/json')
  })
})

describe('storeApi error messages', () => {
  it('shows the API detail string', async () => {
    mockFetch({ ok: false, status: 401, json: async () => ({ detail: 'Invalid email or password' }) })
    await expect(storeApi.login({})).rejects.toThrow('Invalid email or password')
  })

  it('flattens FastAPI validation errors', async () => {
    mockFetch({ ok: false, status: 422, json: async () => ({ detail: [{ msg: 'Field required' }] }) })
    await expect(storeApi.login({})).rejects.toThrow('Field required')
  })

  it('reports server errors with the HTTP status', async () => {
    mockFetch({ ok: false, status: 500, json: async () => { throw new Error('not json') } })
    await expect(storeApi.me()).rejects.toThrow(/HTTP 500/)
  })

  it('reports an unreachable server', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(storeApi.me()).rejects.toThrow(/Cannot reach the server/)
  })
})
