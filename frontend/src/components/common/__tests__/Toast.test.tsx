import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { Toast } from '../Toast'

describe('Toast Component', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders success toast message with icon and styles', () => {
    render(<Toast type="success" message="Preferences saved successfully!" onClose={vi.fn()} />)

    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
    expect(screen.getByText('Preferences saved successfully!')).toBeInTheDocument()
    expect(alert).toHaveAttribute('data-toast-type', 'success')
  })

  it('renders error toast message properly', () => {
    render(<Toast type="error" message="Something went wrong!" onClose={vi.fn()} />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveAttribute('data-toast-type', 'error')
    expect(screen.getByText('Something went wrong!')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn()
    render(<Toast type="info" message="Information note" onClose={handleClose} />)

    const closeBtn = screen.getByRole('button', { name: /close notification/i })
    fireEvent.click(closeBtn)

    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('auto-dismisses after the specified duration', () => {
    const handleClose = vi.fn()
    render(<Toast type="warning" message="Warning timeout" duration={3000} onClose={handleClose} />)

    expect(handleClose).not.toHaveBeenCalled()
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(handleClose).toHaveBeenCalledTimes(1)
  })
})
