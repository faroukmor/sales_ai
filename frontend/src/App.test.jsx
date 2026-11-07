import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { baseResponse } from './test/fixtures'

beforeEach(() => { sessionStorage.clear() })
afterEach(() => { vi.restoreAllMocks() })

describe('GEANT Chat UI', () => {
  it('renders welcome prompts and submits a real request', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => baseResponse })
    render(<App />)
    expect(screen.getByText('Welcome to GEANT Chat UI')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Find a laptop under 100000 DA' }))
    await screen.findByText('I found one product.')
    expect(screen.getByText('TEST-LAPTOP-01')).toBeInTheDocument()
    expect(screen.getByText('Demo product')).toBeInTheDocument()
  })

  it('shows a loading indicator while waiting', async () => {
    let resolve
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise((done) => { resolve = done }))
    render(<App />)
    await userEvent.type(screen.getByLabelText('Message'), 'Find a laptop')
    await userEvent.click(screen.getByLabelText('Send message'))
    expect(screen.getByLabelText('Assistant is thinking')).toBeInTheDocument()
    resolve({ ok: true, json: async () => baseResponse })
    await screen.findByText('I found one product.')
  })

  it('reports a failed request and retries it', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Service unavailable' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => baseResponse })
    render(<App />)
    await userEvent.type(screen.getByLabelText('Message'), 'Find a laptop')
    await userEvent.click(screen.getByLabelText('Send message'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable')
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    await screen.findByText('I found one product.')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('starts a new chat and clears browser session context', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => baseResponse })
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: 'Show available promotions' }))
    await screen.findByText('I found one product.')
    expect(sessionStorage.getItem('geant-chat-session')).toBe(baseResponse.session_id)
    await userEvent.click(screen.getByRole('button', { name: /new conversation/i }))
    expect(screen.getByText('Welcome to GEANT Chat UI')).toBeInTheDocument()
    expect(sessionStorage.getItem('geant-chat-session')).toBeNull()
  })

  it('marks Arabic messages as RTL', async () => {
    const arabic = { ...baseResponse, answer: 'وجدت منتج مطابق', language: 'ar' }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => arabic })
    render(<App />)
    await userEvent.type(screen.getByLabelText('Message'), 'نحب حاسوب محمول')
    await userEvent.keyboard('{Enter}')
    const response = await screen.findByText('وجدت منتج مطابق')
    await waitFor(() => expect(response.closest('.message-row')).toHaveAttribute('dir', 'rtl'))
  })
})
