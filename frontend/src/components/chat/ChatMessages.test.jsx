import { StrictMode } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ChatMessages from './ChatMessages'

const messages = [
  {
    id: 'message-1',
    role: 'user',
    text: 'Find a laptop',
    at: new Date('2026-11-04T09:00:00Z'),
  },
]

describe('ChatMessages effects', () => {
  it('sets up, reruns, and unmounts safely in StrictMode', () => {
    const scroll = vi.spyOn(Element.prototype, 'scrollIntoView')
      // Reproduce a browser/polyfill that returns a non-function value.
      .mockReturnValue({ scrolling: true })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    const view = render(
      <StrictMode><ChatMessages messages={messages} loading={false} /></StrictMode>,
    )

    expect(screen.getByText('Find a laptop')).toBeInTheDocument()
    expect(scroll).toHaveBeenCalledWith({ behavior: 'smooth', block: 'end' })

    view.rerender(
      <StrictMode><ChatMessages messages={messages} loading /></StrictMode>,
    )
    expect(screen.getByLabelText('Assistant is thinking')).toBeInTheDocument()
    expect(() => view.unmount()).not.toThrow()
    expect(consoleError).not.toHaveBeenCalledWith(
      expect.stringContaining('useEffect must not return anything'),
    )
  })
})
