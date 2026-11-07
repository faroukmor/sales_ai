import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import AppErrorBoundary from './components/common/AppErrorBoundary'

describe('full application rendering smoke test', () => {
  it('mounts the entire UI before any backend request', () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Backend offline'))
    render(<AppErrorBoundary><App /></AppErrorBoundary>)

    expect(screen.getByText('GEANT')).toBeInTheDocument()
    expect(screen.getByText('Welcome to GEANT Chat UI')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Find a laptop under 100000 DA' })).toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toBeInTheDocument()
  })

  it('renders when browser session storage is unavailable', () => {
    const original = Object.getOwnPropertyDescriptor(window, 'sessionStorage')
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      get() { throw new DOMException('Access denied', 'SecurityError') },
    })
    try {
      render(<AppErrorBoundary><App /></AppErrorBoundary>)
      expect(screen.getByText('Welcome to GEANT Chat UI')).toBeInTheDocument()
    } finally {
      Object.defineProperty(window, 'sessionStorage', original)
    }
  })

  it('shows a useful fallback for an unexpected render error', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    function BrokenTree() { throw new Error('render failed') }
    render(<AppErrorBoundary><BrokenTree /></AppErrorBoundary>)
    expect(screen.getByRole('alert')).toHaveTextContent('The interface could not start')
    expect(screen.getByRole('button', { name: /reload application/i })).toBeInTheDocument()
  })
})
