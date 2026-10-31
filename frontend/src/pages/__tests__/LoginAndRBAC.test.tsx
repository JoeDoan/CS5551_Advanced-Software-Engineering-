import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App, { AppRoutes } from '../../App'
import { AuthProvider } from '../../context/AuthContext'
import {
  apiClient,
  ApiError,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from '../../services/apiClient'
import {
  DEMO_COORDINATOR_TOKEN,
  DEMO_INSTRUCTOR_TOKEN,
} from '../../services/authService'

describe('Login, Session Security Gate, RBAC & Coordinator Catalog/Section CRUD', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    clearAuthToken()
    window.history.pushState({}, '', '/')
  })

  it('signs in as Coordinator, unlocks Courses & Sections and Administration, and signs out cleanly', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('demo-login-coordinator'))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Coordinator Dashboard/i })).toBeInTheDocument()
    })

    expect(getAuthToken()).toBe(DEMO_COORDINATOR_TOKEN)
    expect(screen.getByTestId('session-active-badge')).toBeInTheDocument()
    expect(screen.getByTestId('navbar-role-badge')).toHaveTextContent('COORDINATOR')
    expect(screen.getByText('Courses & Sections')).toBeInTheDocument()
    expect(screen.getByText('Administration')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Administration'))
    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /Administration & Solver Control/i, level: 1 })
      ).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('logout-button'))

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })
    expect(getAuthToken()).toBeNull()
  })

  it('enforces Faculty Instructor RBAC across Sidebar, Edit Requests, Preferences, and /admin + /courses guards', async () => {
    setAuthToken(DEMO_INSTRUCTOR_TOKEN)

    const { unmount } = render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /Faculty Instructor Dashboard/i })
      ).toBeInTheDocument()
    })

    expect(screen.getByTestId('navbar-role-badge')).toHaveTextContent('INSTRUCTOR')
    expect(screen.getByText('Dr. Yugyung Lee')).toBeInTheDocument()
    expect(screen.queryByText('Courses & Sections')).not.toBeInTheDocument()
    expect(screen.queryByText('Administration')).not.toBeInTheDocument()
    expect(screen.queryByTestId('approve-request-1')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Instructor Prefs'))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Instructor Preferences/i })).toBeInTheDocument()
    })
    const instructorSelect = screen.getByTestId('instructor-select') as HTMLSelectElement
    expect(instructorSelect.value).toBe('1')
    expect(instructorSelect).toBeDisabled()

    unmount()

    const adminRender = render(
      <MemoryRouter initialEntries={['/admin']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('role-guard-403')).toBeInTheDocument()
    })
    expect(screen.getByText(/Coordinator Role Required/i)).toBeInTheDocument()
    adminRender.unmount()

    render(
      <MemoryRouter initialEntries={['/courses']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('role-guard-403')).toBeInTheDocument()
    })
  })

  it('clears expired tokens and redirects to /login with reason when /auth/me returns 401', async () => {
    setAuthToken('expired-jwt-token')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError('Token expired', 401)
    )

    render(
      <MemoryRouter initialEntries={['/schedule']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })
    expect(getAuthToken()).toBeNull()
    expect(screen.getByText(/Your session expired\. Please sign in again\./i)).toBeInTheDocument()
  })

  it('creates a new course and schedules a section in CatalogManagementPage while surfacing 409 conflicts', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)

    render(
      <MemoryRouter initialEntries={['/courses']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('catalog-management-page')).toBeInTheDocument()
      expect(screen.getByText('CS 101')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('add-course-btn'))
    fireEvent.change(screen.getByTestId('modal-course-code'), {
      target: { value: 'CS 495' },
    })
    fireEvent.change(screen.getByTestId('modal-course-name'), {
      target: { value: 'Distributed Cloud Systems' },
    })
    fireEvent.click(screen.getByTestId('save-course-btn'))

    await waitFor(() => {
      expect(screen.getByText('Added CS 495')).toBeInTheDocument()
    })

    const cs495Row = screen.getByText('CS 495').closest('tr')
    expect(cs495Row).not.toBeNull()
    const scheduleCourseBtn = within(cs495Row as HTMLElement).getByRole('button', {
      name: /Schedule Section/i,
    })
    fireEvent.click(scheduleCourseBtn)

    await waitFor(() => {
      expect(screen.getByTestId('modal-section-course')).toBeInTheDocument()
    })

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError('Room RH 204 is already double-booked for MW 08:00-09:15', 409)
    )
    fireEvent.click(screen.getByTestId('save-section-btn'))

    await waitFor(() => {
      expect(
        screen.getAllByText(/Room RH 204 is already double-booked for MW 08:00-09:15/i).length
      ).toBeGreaterThan(0)
    })

    fireEvent.click(screen.getByTestId('save-section-btn'))

    let createdSectionRow: HTMLElement | null = null
    await waitFor(() => {
      const sectionTable = screen.getByTestId('section-manager')
      const cs495SectionCell = within(sectionTable).getByText('CS 495')
      expect(cs495SectionCell).toBeInTheDocument()
      createdSectionRow = cs495SectionCell.closest('tr')
      expect(createdSectionRow).not.toBeNull()
    })

    const sectionButtons = within(createdSectionRow!).getAllByRole('button')
    fireEvent.click(sectionButtons[0])

    await waitFor(() => {
      expect(screen.getByTestId('modal-section-room')).toBeInTheDocument()
    })
    fireEvent.change(screen.getByTestId('modal-section-room'), {
      target: { value: '3' },
    })
    fireEvent.click(screen.getByTestId('save-section-btn'))

    await waitFor(() => {
      expect(within(createdSectionRow!).getByText('FH 256')).toBeInTheDocument()
    })

    const updatedButtons = within(createdSectionRow!).getAllByRole('button')
    fireEvent.click(updatedButtons[1])

    await waitFor(() => {
      const sectionTable = screen.getByTestId('section-manager')
      expect(within(sectionTable).queryByText('CS 495')).not.toBeInTheDocument()
    })
  })
})
