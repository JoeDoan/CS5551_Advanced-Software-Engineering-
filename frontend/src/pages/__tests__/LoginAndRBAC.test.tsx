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
  authService,
  resetMockAccounts,
} from '../../services/authService'
import { resetMockCourseAssignments } from '../../services/courseAssignmentService'
import { preferenceService } from '../../services/preferenceService'

describe('Login, Session Security Gate, RBAC & Coordinator Catalog/Section/Account CRUD', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    clearAuthToken()
    resetMockAccounts()
    resetMockCourseAssignments()
    window.history.pushState({}, '', '/')
  })

  it('signs in as Coordinator, unlocks Courses & Sections, User Accounts, Instructor Prefs, and Administration, and signs out cleanly', async () => {
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
    expect(screen.getByText('Instructor Prefs')).toBeInTheDocument()
    expect(screen.getByText('Administration')).toBeInTheDocument()

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

  it('allows Course Coordinators to inspect /preferences in strict read-only mode across faculty profiles without mutation controls', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)
    const getPrefsSpy = vi
      .spyOn(preferenceService, 'getPreferences')
      .mockImplementation(async (filters) => {
        if (filters?.user_id === 1) {
          return [
            {
              id: 77,
              user_id: 1,
              semester_id: 5,
              course_id: null,
              preferred_days: ['T', 'R'],
              preferred_slots: ['09:30-10:45'],
              preferred_rooms: ['RH 204'],
            },
          ]
        }
        return []
      })

    render(
      <MemoryRouter initialEntries={['/preferences']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Instructor Preferences/i })).toBeInTheDocument()
      expect(screen.getByTestId('coordinator-readonly-banner')).toBeInTheDocument()
    })

    expect(screen.queryByTestId('role-guard-403')).not.toBeInTheDocument()
    expect(screen.getByText('Instructor Prefs')).toBeInTheDocument()
    expect(screen.getByText('Read-Only View')).toBeInTheDocument()
    expect(screen.getByTestId('coordinator-readonly-banner')).toHaveTextContent(
      /View-Only Mode: Course Coordinators can inspect faculty availability profiles\./i
    )

    const instructorSelect = screen.getByTestId('instructor-select') as HTMLSelectElement
    expect(instructorSelect).not.toBeDisabled()
    await waitFor(() => {
      expect(instructorSelect.value).toBe('1')
    })

    const slotBtn = await screen.findByTestId('slot-09:30-10:45')
    const roomChip = await screen.findByTestId('room-chip-RH 204')

    await waitFor(() => {
      expect(screen.getByTestId('day-btn-Tuesday (T)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Thursday (R)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Monday (M)')).toHaveAttribute('aria-pressed', 'false')
      expect(slotBtn).toHaveAttribute('aria-pressed', 'true')
      expect(slotBtn.className).toContain('bg-blue-50')
      expect(roomChip).toHaveAttribute('aria-pressed', 'true')
      expect(roomChip.className).toContain('bg-blue-50')
    })

    expect(screen.getByTestId('day-btn-Tuesday (T)')).toBeDisabled()
    expect(screen.getByTestId('day-btn-Monday (M)')).toBeDisabled()
    expect(slotBtn).toBeDisabled()
    expect(roomChip).toBeDisabled()

    expect(screen.queryByTestId('preset-days-mwf')).not.toBeInTheDocument()
    expect(screen.queryByTestId('preset-days-tr')).not.toBeInTheDocument()
    expect(screen.queryByTestId('preset-days-all')).not.toBeInTheDocument()
    expect(screen.queryByTestId('save-preferences-button')).not.toBeInTheDocument()
    expect(screen.queryByTestId('reset-preferences-button')).not.toBeInTheDocument()
    expect(screen.queryByTestId('edit-pref-77')).not.toBeInTheDocument()
    expect(screen.queryByTestId('delete-pref-77')).not.toBeInTheDocument()

    fireEvent.change(instructorSelect, { target: { value: '2' } })

    await waitFor(() => {
      expect(getPrefsSpy).toHaveBeenCalledWith({
        user_id: 2,
        semester_id: 5,
        general_only: true,
      })
      expect(screen.getByTestId('day-btn-Tuesday (T)')).toHaveAttribute('aria-pressed', 'false')
      expect(slotBtn).toHaveAttribute('aria-pressed', 'false')
      expect(roomChip).toHaveAttribute('aria-pressed', 'false')
      expect(
        screen.getByText('No saved preferences recorded for this instructor in Fall 2026 yet.')
      ).toBeInTheDocument()
    })
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
    expect(solverBtn).toHaveTextContent('Execute Solver (Fall 2026)')

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

  it('locks logged-in Instructor to Current Term Fall 2026 on /schedule and /preferences and hides past semester and course selectors', async () => {
    setAuthToken(DEMO_INSTRUCTOR_TOKEN)

    render(
      <MemoryRouter initialEntries={['/schedule']}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('active-semester-badge')).toHaveTextContent(
        'Current Term: Fall 2026'
      )
    })
    expect(screen.queryByTestId('semester-select')).not.toBeInTheDocument()
    expect(screen.queryByTestId('open-semester-comparison-btn')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Instructor Prefs'))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Instructor Preferences/i })).toBeInTheDocument()
    })
    expect(screen.getByTestId('active-semester-badge')).toHaveTextContent(
      'Current Term: Fall 2026'
    )
    expect(screen.queryByTestId('preference-semester-select')).not.toBeInTheDocument()
    expect(screen.queryByTestId('preference-course-select')).not.toBeInTheDocument()
    expect(screen.getByTestId('coordinator-assigned-courses')).toBeInTheDocument()
  })

  it('allows Coordinator on /courses to filter by Department and Course Level and assign multiple courses to an instructor', async () => {
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
    })

    fireEvent.click(screen.getByTestId('tab-assignments'))

    const manager = await screen.findByTestId('faculty-assignment-manager')
    await waitFor(() => {
      expect(within(manager).getByTestId('assign-course-toggle-3')).toBeInTheDocument()
    })

    fireEvent.change(within(manager).getByTestId('assignment-dept-filter'), {
      target: { value: 'CS' },
    })
    fireEvent.change(within(manager).getByTestId('assignment-level-filter'), {
      target: { value: 'undergraduate' },
    })

    expect(within(manager).getByTestId('assign-course-toggle-3')).toBeInTheDocument()
    expect(within(manager).queryByTestId('assign-course-toggle-5')).not.toBeInTheDocument()
    expect(within(manager).queryByTestId('assign-course-toggle-6')).not.toBeInTheDocument()

    fireEvent.click(within(manager).getByTestId('assign-course-toggle-3'))

    fireEvent.change(within(manager).getByTestId('assignment-level-filter'), {
      target: { value: 'graduate' },
    })

    expect(within(manager).getByTestId('assign-course-toggle-5')).toBeInTheDocument()
    expect(within(manager).queryByTestId('assign-course-toggle-3')).not.toBeInTheDocument()

    fireEvent.click(within(manager).getByTestId('assign-course-toggle-5'))
    fireEvent.click(within(manager).getByTestId('save-instructor-assignments-btn'))

    await waitFor(() => {
      const summary = within(manager).getByTestId('instructor-assignment-summary-1')
      expect(summary).toHaveTextContent('Dr. Yugyung Lee')
      expect(summary).toHaveTextContent('CS 303 · Undergraduate')
      expect(summary).toHaveTextContent('CS 5551 · Graduate')
    })

    fireEvent.click(screen.getByTestId('tab-sections'))
    const sectionMgr = await screen.findByTestId('section-manager')
    fireEvent.click(within(sectionMgr).getByTestId('add-section-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('modal-section-dept-filter')).toBeInTheDocument()
      expect(screen.getByTestId('modal-section-level-filter')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('modal-section-dept-filter'), {
      target: { value: 'CS' },
    })
    fireEvent.change(screen.getByTestId('modal-section-level-filter'), {
      target: { value: 'graduate' },
    })

    await waitFor(() => {
      const courseSelect = screen.getByTestId('modal-section-course') as HTMLSelectElement
      expect(courseSelect.value).toBe('5')
      expect(courseSelect).toHaveTextContent('CS 5551 [Graduate]')

      const roomSelect = screen.getByTestId('modal-section-room')
      expect(roomSelect).toHaveTextContent('RH 204 — Royall Hall')
      expect(roomSelect).toHaveTextContent('FH 464 — Flarsheim Hall')
    })
  })

  it('hydrates 1-click Faculty Instructor demo login dynamically from /auth/demo-accounts on UIUC FOIA profile', async () => {
    vi.spyOn(authService, 'getDemoAccounts').mockResolvedValue([
      {
        email: 'coordinator@umkc.edu',
        username: 'coordinator',
        full_name: 'Course Coordinator',
        role: 'coordinator',
        department: 'CS',
        password: 'coordinator123',
        linked_user_id: null,
      },
      {
        email: 'leeh@illinois.edu',
        username: 'leeh',
        full_name: 'Dr. Hyoeun Lee',
        role: 'instructor',
        department: 'BIOE',
        password: 'faculty123',
        linked_user_id: 1,
      },
    ])
    const loginSpy = vi.spyOn(authService, 'login').mockResolvedValue({
      access_token: 'foia-instructor-jwt',
      token_type: 'bearer',
      session_id: 'foia-session-1',
      expires_at: new Date(Date.now() + 3600_000).toISOString(),
      user: {
        id: 101,
        email: 'leeh@illinois.edu',
        username: 'leeh',
        full_name: 'Dr. Hyoeun Lee',
        role: 'instructor',
        department: 'BIOE',
        linked_user_id: 1,
      },
    })

    render(<App />)

    const demoFacultyBtn = await screen.findByTestId('demo-login-instructor')
    await waitFor(() => {
      expect(demoFacultyBtn).toHaveTextContent('leeh@illinois.edu (Dr. Hyoeun Lee)')
    })

    fireEvent.click(demoFacultyBtn)

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith({
        identifier: 'leeh@illinois.edu',
        password: 'faculty123',
      })
      expect(
        screen.getByRole('heading', { name: /Faculty Instructor Dashboard/i })
      ).toBeInTheDocument()
      expect(screen.getByText('Dr. Hyoeun Lee')).toBeInTheDocument()
    })
  })
})
