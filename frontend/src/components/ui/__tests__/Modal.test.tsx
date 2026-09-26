import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Modal } from '../Modal'
import { Button } from '../Button'

describe('Modal UI Component', () => {
  it('does not render when isOpen is false', () => {
    render(
      <Modal isOpen={false} onClose={() => {}} title="Test Modal">
        Modal Content
      </Modal>
    )

    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument()
  })

  it('renders modal title, description, content, and footer when open', () => {
    const handleClose = vi.fn()
    render(
      <Modal
        isOpen={true}
        onClose={handleClose}
        title="Event Details"
        description="Course information"
        footer={<Button onClick={handleClose}>Confirm</Button>}
      >
        <p>CS 5551 in FH 256</p>
      </Modal>
    )

    expect(screen.getByText('Event Details')).toBeInTheDocument()
    expect(screen.getByText('Course information')).toBeInTheDocument()
    expect(screen.getByText('CS 5551 in FH 256')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()

    // Test close button
    const closeBtn = screen.getByRole('button', { name: /close modal/i })
    fireEvent.click(closeBtn)
    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('closes on Escape key press', () => {
    const handleClose = vi.fn()
    render(
      <Modal isOpen={true} onClose={handleClose} title="Escape Test">
        Content
      </Modal>
    )

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(handleClose).toHaveBeenCalledTimes(1)
  })
})
