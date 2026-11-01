import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import App from './App'
import { clearAuthToken, setAuthToken } from './services/apiClient'
import { DEMO_COORDINATOR_TOKEN } from './services/authService'

describe('App Route Navigation Shell & Security Gate', () => {
  beforeEach(() => {
    clearAuthToken()
    window.history.pushState({}, '', '/')
  })

  it('gates unauthenticated visitors at the login screen', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })
    expect(screen.getByText(/Sign in to your account/i)).toBeInTheDocument()
    expect(screen.getByTestId('demo-login-coordinator')).toBeInTheDocument()
    expect(screen.getByTestId('demo-login-instructor')).toBeInTheDocument()
  })

  it('renders application navigation shell and dashboard for authenticated coordinators', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)
    render(<App />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Coordinator Dashboard/i })).toBeInTheDocument()
    })
    expect(screen.getByText(/UMKC Scheduler/i)).toBeInTheDocument()
    expect(screen.getByText('Master Schedule')).toBeInTheDocument()
    expect(screen.getByText('Courses & Sections')).toBeInTheDocument()
    expect(screen.getByText('User Accounts')).toBeInTheDocument()
    expect(screen.getByText('Instructor Prefs')).toBeInTheDocument()
    expect(screen.getByText('Administration')).toBeInTheDocument()
    expect(screen.getByText(/CS 5551 Project/i)).toBeInTheDocument()
  })
})
