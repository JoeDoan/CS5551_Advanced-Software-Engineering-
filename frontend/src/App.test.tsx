import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App Route Navigation Shell', () => {
  it('renders application navigation shell and dashboard by default', () => {
    render(<App />)
    expect(screen.getByText(/UMKC Scheduler/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Coordinator Dashboard/i })).toBeInTheDocument()
    expect(screen.getByText('Master Schedule')).toBeInTheDocument()
    expect(screen.getByText('Instructor Prefs')).toBeInTheDocument()
    expect(screen.getByText('Administration')).toBeInTheDocument()
    expect(screen.getByText(/CS 5551 Project/i)).toBeInTheDocument()
  })
})
