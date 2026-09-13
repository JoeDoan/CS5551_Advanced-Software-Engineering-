import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Navbar } from '../Navbar'

describe('Navbar Component', () => {
  it('renders branding title correctly', () => {
    render(<Navbar />)
    expect(screen.getByText(/UMKC Scheduler/i)).toBeInTheDocument()
    expect(screen.getByText(/Sprint 0/i)).toBeInTheDocument()
  })

  it('renders solver ready badge and coordinator profile', () => {
    render(<Navbar />)
    expect(screen.getByText(/Solver: Ready/i)).toBeInTheDocument()
    expect(screen.getByText(/Course Coordinator/i)).toBeInTheDocument()
  })
})
