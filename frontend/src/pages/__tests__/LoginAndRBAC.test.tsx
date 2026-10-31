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
  resetMockAccounts,
} from '../../services/authService'

describe('Login, Session Security Gate, RBAC & Coordinator Catalog/Section/Account CRUD', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    clearAuthToken()
    resetMockAccounts()
    window.history.pushState({}, '', '/')
  })

  it('signs in as Coordinator, unlocks Courses & Sections, User Accounts, and Administration, and signs out cleanly', async () => {
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
    expect(screen.getByText('User Accounts')).toBeInTheDocument()
    expect(screen.getByText('Administration')).toBeInTheDocument()
    expect(screen.queryByText('Instructor Prefs')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Administration'))
    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /Administration & Solver Control/i, level: 1 })
      ).toBeInTheDocument()
    })
    expect(screen.getByTestId('manage-user-accounts-btn')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('logout-button'))

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })
    expect(getAuthToken()).toBeNull()
  })

  it('blocks Course Coordinators from accessing /preferences with Faculty Instructor Role Required 403 guard', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)

    render(
      <MemoryRouter initialEntries={['/preferences']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('role-guard-403')).toBeInTheDocument()
    })
    expect(screen.getByText(/Faculty Instructor Role Required/i)).toBeInTheDocument()
    expect(screen.queryByText('Instructor Prefs')).not.toBeInTheDocument()
    expect(screen.getByTestId('return-to-schedule-btn')).toHaveTextContent('Return to Dashboard')
  })

  it('enforces Faculty Instructor RBAC across Sidebar, Edit Requests, Preferences, and /admin + /courses + /users guards', async () => {
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
    expect(screen.queryByText('User Accounts')).not.toBeInTheDocument()
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

    const coursesRender = render(
      <MemoryRouter initialEntries={['/courses']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('role-guard-403')).toBeInTheDocument()
    })
    coursesRender.unmount()

    const usersRender = render(
      <MemoryRouter initialEntries={['/users']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('role-guard-403')).toBeInTheDocument()
    })
    expect(screen.getByText(/Coordinator Role Required/i)).toBeInTheDocument()
    usersRender.unmount()
  })

  it('allows Coordinator to navigate to /users and provision both Faculty Instructor and Coordinator accounts', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)

    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Coordinator Dashboard/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('User Accounts'))

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /User & Role Management/i, level: 1 })
      ).toBeInTheDocument()
      expect(screen.getByTestId('account-manager')).toBeInTheDocument()
      expect(screen.getByText('raopr@umkc.edu')).toBeInTheDocument()
    })

    expect(screen.getByTestId('coordinator-count-badge')).toHaveTextContent('1 Coordinator')
    expect(screen.getByTestId('instructor-count-badge')).toHaveTextContent('2 Instructors')
    expect(screen.getByTestId('toggle-account-100')).toBeDisabled()
    expect(screen.getByTestId('delete-account-100')).toBeDisabled()

    fireEvent.click(screen.getByTestId('create-account-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('modal-account-role')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('modal-account-role'), {
      target: { value: 'instructor' },
    })
    fireEvent.change(screen.getByTestId('modal-account-fullname'), {
      target: { value: 'Dr. Alan Turing' },
    })
    fireEvent.change(screen.getByTestId('modal-account-email'), {
      target: { value: 'turinga@umkc.edu' },
    })
    expect((screen.getByTestId('modal-account-username') as HTMLInputElement).value).toBe(
      'turinga'
    )
    fireEvent.change(screen.getByTestId('modal-account-department'), {
      target: { value: 'CS' },
    })
    fireEvent.change(screen.getByTestId('modal-account-password'), {
      target: { value: 'turingpass123' },
    })

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError('Account with email turinga@umkc.edu already exists', 409)
    )
    fireEvent.click(screen.getByTestId('save-account-btn'))

    await waitFor(() => {
      expect(
        screen.getByText(/Account with email turinga@umkc.edu already exists/i)
      ).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('save-account-btn'))

    await waitFor(() => {
      const manager = screen.getByTestId('account-manager')
      expect(within(manager).getByText('Dr. Alan Turing')).toBeInTheDocument()
      expect(within(manager).getByText('@turinga')).toBeInTheDocument()
      expect(within(manager).getByText('turinga@umkc.edu')).toBeInTheDocument()
      expect(within(manager).getByText('Faculty #3')).toBeInTheDocument()
    })
    expect(screen.getByTestId('instructor-count-badge')).toHaveTextContent('3 Instructors')

    fireEvent.click(screen.getByTestId('create-account-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('modal-account-role')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('modal-account-role'), {
      target: { value: 'coordinator' },
    })
    fireEvent.change(screen.getByTestId('modal-account-fullname'), {
      target: { value: 'Dr. Ada Lovelace' },
    })
    fireEvent.change(screen.getByTestId('modal-account-email'), {
      target: { value: 'lovelacea@umkc.edu' },
    })
    fireEvent.change(screen.getByTestId('modal-account-department'), {
      target: { value: 'MATH' },
    })
    fireEvent.change(screen.getByTestId('modal-account-password'), {
      target: { value: 'lovelace123' },
    })
    fireEvent.click(screen.getByTestId('save-account-btn'))

    await waitFor(() => {
      const manager = screen.getByTestId('account-manager')
      const adaRow = within(manager).getByText('Dr. Ada Lovelace').closest('tr')
      expect(adaRow).not.toBeNull()
      expect(within(adaRow as HTMLElement).getByText('@lovelacea')).toBeInTheDocument()
      expect(within(adaRow as HTMLElement).getByText('COORDINATOR')).toBeInTheDocument()
      expect(within(adaRow as HTMLElement).getByText('MATH')).toBeInTheDocument()
      expect(within(adaRow as HTMLElement).getByText('Admin Portal')).toBeInTheDocument()
    })
    expect(screen.getByTestId('coordinator-count-badge')).toHaveTextContent('2 Coordinators')
  })

  it('reaches /users from AdminPage quick-action and supports editing, disabling, filtering, and deleting accounts', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('manage-user-accounts-btn')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('manage-user-accounts-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('account-manager')).toBeInTheDocument()
      expect(screen.getByText('Dr. Praveen Rao')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('edit-account-102'))

    await waitFor(() => {
      expect(screen.getByTestId('modal-account-email')).toBeDisabled()
      expect(screen.getByTestId('modal-account-username')).toBeDisabled()
    })

    fireEvent.change(screen.getByTestId('modal-account-department'), {
      target: { value: 'ECE' },
    })
    fireEvent.change(screen.getByTestId('modal-account-password'), {
      target: { value: 'resetpass123' },
    })
    fireEvent.click(screen.getByTestId('save-account-btn'))

    await waitFor(() => {
      const raoRow = screen.getByText('Dr. Praveen Rao').closest('tr')
      expect(raoRow).not.toBeNull()
      expect(within(raoRow as HTMLElement).getByText('ECE')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('toggle-account-102'))

    await waitFor(() => {
      const raoRow = screen.getByText('Dr. Praveen Rao').closest('tr')
      expect(within(raoRow as HTMLElement).getByText('Disabled')).toBeInTheDocument()
    })

    const manager = screen.getByTestId('account-manager')
    fireEvent.change(screen.getByTestId('account-role-filter'), {
      target: { value: 'coordinator' },
    })
    expect(within(manager).queryByText('Dr. Praveen Rao')).not.toBeInTheDocument()
    expect(within(manager).getByText('Course Coordinator')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('account-role-filter'), {
      target: { value: 'ALL' },
    })
    fireEvent.change(screen.getByTestId('account-search-input'), {
      target: { value: 'raopr' },
    })
    expect(within(manager).getByText('Dr. Praveen Rao')).toBeInTheDocument()
    expect(within(manager).queryByText('Dr. Yugyung Lee')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('delete-account-102'))

    await waitFor(() => {
      expect(screen.queryByText('Dr. Praveen Rao')).not.toBeInTheDocument()
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

  it('toggles Navbar notifications popover, updates AdminPage solver target semester, and surfaces real HTTP solver errors', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    const solverBtn = await screen.findByTestId('execute-solver-button')
    expect(solverBtn).toHaveTextContent('Execute Solver (Fall 2024)')

    fireEvent.click(screen.getByTestId('notifications-bell-btn'))
    await waitFor(() => {
      expect(screen.getByTestId('notifications-popover')).toBeInTheDocument()
      expect(screen.getByText('View Full Request Queue')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('admin-semester-select'), {
      target: { value: '3' },
    })
    expect(screen.getByTestId('execute-solver-button')).toHaveTextContent(
      'Execute Solver (Fall 2025)'
    )

    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockRejectedValueOnce(new ApiError('Solver infeasible for Fall 2025', 422))

    fireEvent.click(screen.getByTestId('execute-solver-button'))

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith('/solver/run', { semester_id: 3 })
      expect(screen.getByText('Solver Execution Error')).toBeInTheDocument()
      expect(screen.getByText('Solver infeasible for Fall 2025')).toBeInTheDocument()
    })
  })
})

