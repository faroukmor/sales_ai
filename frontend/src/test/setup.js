import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => cleanup())

Object.defineProperty(window, 'sessionStorage', {
  configurable: true,
  value: (() => { let store = {}; return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} },
  } })(),
})
if (!globalThis.crypto?.randomUUID) {
  Object.defineProperty(globalThis, 'crypto', { value: { randomUUID: vi.fn(() => `${Date.now()}-${Math.random()}`) } })
}
Element.prototype.scrollIntoView = vi.fn()
