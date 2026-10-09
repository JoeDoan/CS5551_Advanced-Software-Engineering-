import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Badge } from '../Badge'

describe('Badge UI Component', () => {
  it('renders badge text correctly', () => {
    render(<Badge>Confirmed</Badge>)
    expect(screen.getByText('Confirmed')).toBeInTheDocument()
  })

  it('renders success variant styling', () => {
    render(<Badge variant="success">Solved</Badge>)
    const badge = screen.getByText('Solved')
    expect(badge.className).toContain('text-emerald-700')
  })

  it('renders department badge classes', () => {
    render(<Badge department="cs">CS Dept</Badge>)
    const badge = screen.getByText('CS Dept')
    expect(badge.className).toContain('badge-dept-cs')
  })

  it('renders with dot indicator', () => {
    const { container } = render(<Badge variant="danger" dot>Conflict</Badge>)
    const dot = container.querySelector('.rounded-full.mr-1\\.5')
    expect(dot).toBeInTheDocument()
  })
})
