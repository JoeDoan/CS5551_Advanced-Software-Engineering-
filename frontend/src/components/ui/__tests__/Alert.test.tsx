import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Alert } from '../Alert'

describe('Alert UI Component', () => {
  it('renders alert title and body content', () => {
    render(
      <Alert title="Schedule Generated">
        All 40 courses have been successfully assigned.
      </Alert>
    )

    expect(screen.getByText('Schedule Generated')).toBeInTheDocument()
    expect(
      screen.getByText('All 40 courses have been successfully assigned.')
    ).toBeInTheDocument()
  })

  it('renders warning variant properly', () => {
    render(
      <Alert variant="warning" title="Constraint Warning">
        Room capacity is nearing threshold.
      </Alert>
    )

    const alertEl = screen.getByRole('alert')
    expect(alertEl.className).toContain('bg-amber-50')
  })

  it('handles close dismiss button click', () => {
    const handleClose = vi.fn()
    render(
      <Alert title="Dismissible Alert" onClose={handleClose}>
        Notice text
      </Alert>
    )

    const closeBtn = screen.getByRole('button', { name: /dismiss alert/i })
    fireEvent.click(closeBtn)
    expect(handleClose).toHaveBeenCalledTimes(1)
  })
})
