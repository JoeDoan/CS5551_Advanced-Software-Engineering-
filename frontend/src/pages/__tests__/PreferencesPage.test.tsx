import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PreferencesPage } from '../PreferencesPage'
import AuthContext, { AuthContextValue, AuthProvider } from '../../context/AuthContext'
import { clearAuthToken, setAuthToken } from '../../services/apiClient'
import { DEMO_COORDINATOR_TOKEN } from '../../services/authService'
import { DEFAULT_INSTRUCTORS, instructorService } from '../../services/instructorService'
import { preferenceService } from '../../services/preferenceService'
import { timeSlotService } from '../../services/timeSlotService'
import { roomService } from '../../services/roomService'
import {
  courseAssignmentService,
  resetMockCourseAssignments,
} from '../../services/courseAssignmentService'
import { scheduleService } from '../../services/scheduleService'

describe('PreferencesPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    clearAuthToken()
    resetMockCourseAssignments()
    vi.spyOn(timeSlotService, 'getTimeSlots').mockResolvedValue([
      { id: 1, day_pattern: 'MW', start_time: '08:00', end_time: '09:15' },
      { id: 2, day_pattern: 'MW', start_time: '09:30', end_time: '10:45' },
      { id: 3, day_pattern: 'MW', start_time: '11:00', end_time: '12:15' },
      {
        id: 9,
        day_pattern: 'TR',
        start_time: '17:30',
        end_time: '18:45',
        level: 'graduate',
      },
    ])
    vi.spyOn(roomService, 'getRooms').mockResolvedValue([
      {
        id: 1,
        room_number: 'RH 204',
        capacity: 48,
        room_type: 'lecture',
        building_id: 1,
      },
      {
        id: 5,
        room_number: 'FH 464',
        capacity: 30,
        room_type: 'lab',
        building_id: 2,
      },
    ])
  })

  it('locks to active Fall 2026 semester without semester selector and defaults course scope selector to general', () => {
    render(<PreferencesPage />)

    expect(screen.getByText('Instructor Preferences')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Instructor')).toBeInTheDocument()
    expect(screen.getByLabelText('Apply Preferences To')).toBeInTheDocument()
    expect(screen.getByTestId('active-semester-badge')).toHaveTextContent(
      'Current Term: Fall 2026'
    )
    const courseSelect = screen.getByTestId('preference-course-select') as HTMLSelectElement
    expect(courseSelect).toBeInTheDocument()
    expect(courseSelect.value).toBe('general')
    expect(screen.queryByTestId('preference-semester-select')).not.toBeInTheDocument()
    expect(screen.getByText('Preferred Days')).toBeInTheDocument()
    expect(screen.getByText('Preferred Time Slots')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save preferences/i })).toBeInTheDocument()
  })

  it('renders time slot ranges without displaying a Grad 5000+ badge on graduate-tagged slots', async () => {
    render(<PreferencesPage />)

    expect(await screen.findByTestId('slot-08:00-09:15')).toHaveTextContent('08:00 - 09:15')
    expect(screen.getByTestId('slot-09:30-10:45')).toBeInTheDocument()
    expect(screen.getByTestId('slot-11:00-12:15')).toBeInTheDocument()
    expect(screen.getByTestId('slot-17:30-18:45')).toHaveTextContent('17:30 - 18:45')
    expect(screen.queryByText(/Grad 5000\+/i)).not.toBeInTheDocument()
  })

  it('displays resolved building names next to room numbers on classroom chips', async () => {
    render(<PreferencesPage />)

    const rhChip = await screen.findByTestId('room-chip-RH 204')
    const fhChip = await screen.findByTestId('room-chip-FH 464')

    expect(rhChip).toHaveTextContent('RH 204')
    expect(rhChip).toHaveTextContent('Royall Hall')
    expect(fhChip).toHaveTextContent('FH 464')
    expect(fhChip).toHaveTextContent('Flarsheim Hall')
  })

  it('renders read-only Coordinator-assigned courses with Undergraduate, Graduate, and 2-year habit status badges', async () => {
    vi.spyOn(courseAssignmentService, 'getAssignments').mockResolvedValue([
      {
        id: 1,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        instructor_department: 'BIOE',
        course_id: 3,
        course_code: 'BIOE 205',
        course_name: 'Signals & Systems in Bioengrg',
        department: 'BIOE',
        course_level: 'undergraduate',
      },
      {
        id: 2,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        instructor_department: 'BIOE',
        course_id: 5,
        course_code: 'BIOE 504',
        course_name: 'Analytical Methods in Bioeng',
        department: 'BIOE',
        course_level: 'graduate',
      },
    ])
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue([])
    vi.spyOn(preferenceService, 'getPreferences').mockImplementation(async (filters) => {
      if (filters?.general_only) return []
      return [
        {
          id: 10,
          user_id: 1,
          semester_id: 5,
          course_id: 3,
          preferred_days: ['Tuesday', 'Thursday'],
          preferred_slots: ['11:00-12:15'],
          preferred_rooms: [],
        },
        {
          id: 11,
          user_id: 1,
          semester_id: 5,
          course_id: 5,
          preferred_days: [],
          preferred_slots: [],
          preferred_rooms: [],
        },
      ]
    })

    render(<PreferencesPage />)

    const assignedCard = screen.getByTestId('coordinator-assigned-courses')
    await waitFor(() => {
      expect(within(assignedCard).getByText('BIOE 205')).toBeInTheDocument()
      expect(within(assignedCard).getByText('Undergraduate')).toBeInTheDocument()
      expect(within(assignedCard).getByTestId('course-habit-badge-3')).toHaveTextContent(
        '2-yr habit: TR 11:00-12:15'
      )
      expect(within(assignedCard).getByText('BIOE 504')).toBeInTheDocument()
      expect(within(assignedCard).getByText('Graduate')).toBeInTheDocument()
      expect(within(assignedCard).getByTestId('course-habit-badge-5')).toHaveTextContent(
        'No preference submitted'
      )
    })
    expect(within(assignedCard).getByTestId('habit-provenance-note')).toHaveTextContent(
      /causal 2-year modal teaching window/i
    )
  })

  it('toggles day and time slot selection buttons', async () => {
    render(<PreferencesPage />)

    const fridayBtn = screen.getByRole('button', { name: 'Friday (F)' })
    fireEvent.click(fridayBtn)
    expect(fridayBtn).toHaveAttribute('aria-pressed', 'true')

    const slotBtn = await screen.findByTestId('slot-09:30-10:45')
    expect(slotBtn.className).toContain('bg-slate-50')

    fireEvent.click(slotBtn)
    expect(slotBtn.className).toContain('bg-blue-50')
    expect(slotBtn.className).toContain('border-blue-600')

    fireEvent.click(slotBtn)
    expect(slotBtn.className).toContain('bg-slate-50')
  })

  it('displays error toast when submitted without day or time slot', async () => {
    render(<PreferencesPage />)

    fireEvent.click(screen.getByRole('button', { name: /save preferences/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Please select at least one teaching day and one time slot.')
      ).toBeInTheDocument()
    })
  })

  it('handles API submission errors gracefully with error toast', async () => {
    vi.spyOn(preferenceService, 'submitPreference').mockRejectedValueOnce(
      new Error('API failure')
    )

    render(<PreferencesPage />)

    fireEvent.click(await screen.findByTestId('slot-11:00-12:15'))
    fireEvent.click(screen.getByRole('button', { name: /save preferences/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Failed to save preferences. Please check backend connection.')
      ).toBeInTheDocument()
    })
  })

  it('resets selected days and slots on Reset button click', async () => {
    render(<PreferencesPage />)

    const slotBtn = await screen.findByTestId('slot-08:00-09:15')
    fireEvent.click(slotBtn)
    expect(slotBtn.className).toContain('bg-blue-50')

    fireEvent.click(screen.getByRole('button', { name: /reset/i }))

    expect(slotBtn.className).toContain('bg-slate-50')
  })

  it('hydrates saved General availability for semester_id 5 on page load', async () => {
    const getPrefsSpy = vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([
      {
        id: 42,
        user_id: 1,
        semester_id: 5,
        course_id: null,
        preferred_days: ['T', 'R'],
        preferred_slots: ['11:00-12:15'],
        preferred_rooms: ['RH 204'],
      },
    ])

    render(<PreferencesPage />)

    const slotBtn = await screen.findByTestId('slot-11:00-12:15')
    const roomChip = await screen.findByTestId('room-chip-RH 204')

    await waitFor(() => {
      expect(getPrefsSpy).toHaveBeenCalledWith({
        user_id: 1,
        semester_id: 5,
        general_only: true,
      })
      expect(screen.getByTestId('day-btn-Tuesday (T)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Thursday (R)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Monday (M)')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('day-btn-Wednesday (W)')).toHaveAttribute('aria-pressed', 'false')
      expect(slotBtn.className).toContain('bg-blue-50')
      expect(roomChip).toHaveAttribute('aria-pressed', 'true')
      expect(roomChip.className).toContain('bg-blue-50')
    })
  })

  it('submits general availability for semester_id 5 with course_id null and selected preferred_rooms, and supports Load & Edit and Delete', async () => {
    vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([])
    const deleteSpy = vi.spyOn(preferenceService, 'deletePreference').mockResolvedValue()
    const submitSpy = vi.spyOn(preferenceService, 'submitPreference').mockResolvedValueOnce({
      id: 205,
      user_id: 1,
      semester_id: 5,
      course_id: null,
      preferred_days: ['T', 'R'],
      preferred_slots: ['17:30-18:45'],
      preferred_rooms: ['RH 204', 'FH 464'],
    })

    render(<PreferencesPage />)

    await screen.findByTestId('room-chip-RH 204')

    fireEvent.click(screen.getByTestId('preset-days-tr'))
    fireEvent.click(screen.getByTestId('slot-17:30-18:45'))
    fireEvent.click(screen.getByTestId('room-chip-RH 204'))
    fireEvent.click(screen.getByTestId('room-chip-FH 464'))

    fireEvent.click(screen.getByTestId('save-preferences-button'))

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith({
        user_id: 1,
        semester_id: 5,
        course_id: null,
        preferred_days: ['T', 'R'],
        preferred_slots: ['17:30-18:45'],
        preferred_rooms: ['RH 204', 'FH 464'],
      })
      expect(screen.getByText('Instructor preferences saved successfully!')).toBeInTheDocument()
      expect(screen.getByTestId('edit-pref-205')).toBeInTheDocument()
      expect(screen.getByTestId('delete-pref-205')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('reset-preferences-button'))
    expect(screen.getByTestId('room-chip-RH 204')).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(screen.getByTestId('edit-pref-205'))
    await waitFor(() => {
      expect(screen.getByTestId('room-chip-RH 204')).toHaveAttribute('aria-pressed', 'true')
    })

    fireEvent.click(screen.getByTestId('delete-pref-205'))

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith(205)
      expect(screen.queryByTestId('delete-pref-205')).not.toBeInTheDocument()
    })
  })

  it('prevents Course Coordinators from mutating displayed day, slot, or room selections when clicked', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)
    vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([
      {
        id: 88,
        user_id: 1,
        semester_id: 5,
        course_id: null,
        preferred_days: ['T', 'R'],
        preferred_slots: ['11:00-12:15'],
        preferred_rooms: ['RH 204'],
      },
    ])

    render(
      <AuthProvider>
        <PreferencesPage />
      </AuthProvider>
    )

    await screen.findByTestId('coordinator-readonly-banner')
    const selectedDayBtn = screen.getByTestId('day-btn-Tuesday (T)')
    const unselectedDayBtn = screen.getByTestId('day-btn-Friday (F)')
    const selectedSlotBtn = await screen.findByTestId('slot-11:00-12:15')
    const unselectedSlotBtn = await screen.findByTestId('slot-08:00-09:15')
    const selectedRoomBtn = await screen.findByTestId('room-chip-RH 204')
    const unselectedRoomBtn = await screen.findByTestId('room-chip-FH 464')

    await waitFor(() => {
      expect(selectedDayBtn).toHaveAttribute('aria-pressed', 'true')
      expect(unselectedDayBtn).toHaveAttribute('aria-pressed', 'false')
      expect(selectedSlotBtn).toHaveAttribute('aria-pressed', 'true')
      expect(unselectedSlotBtn).toHaveAttribute('aria-pressed', 'false')
      expect(selectedRoomBtn).toHaveAttribute('aria-pressed', 'true')
      expect(unselectedRoomBtn).toHaveAttribute('aria-pressed', 'false')
    })

    fireEvent.click(selectedDayBtn)
    fireEvent.click(unselectedDayBtn)
    fireEvent.click(selectedSlotBtn)
    fireEvent.click(unselectedSlotBtn)
    fireEvent.click(selectedRoomBtn)
    fireEvent.click(unselectedRoomBtn)

    expect(selectedDayBtn).toHaveAttribute('aria-pressed', 'true')
    expect(unselectedDayBtn).toHaveAttribute('aria-pressed', 'false')
    expect(selectedSlotBtn).toHaveAttribute('aria-pressed', 'true')
    expect(selectedSlotBtn.className).toContain('bg-blue-50')
    expect(unselectedSlotBtn).toHaveAttribute('aria-pressed', 'false')
    expect(unselectedSlotBtn.className).toContain('bg-slate-50')
    expect(selectedRoomBtn).toHaveAttribute('aria-pressed', 'true')
    expect(selectedRoomBtn.className).toContain('bg-blue-50')
    expect(unselectedRoomBtn).toHaveAttribute('aria-pressed', 'false')
    expect(unselectedRoomBtn.className).toContain('bg-slate-50')
  })

  it('locks Select Instructor to authenticated Dr. Hyoeun Lee without flashing or displaying Dr. Yugyung Lee', async () => {
    const getInstructorsSpy = vi
      .spyOn(instructorService, 'getInstructors')
      .mockResolvedValue(DEFAULT_INSTRUCTORS)
    vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([])
    vi.spyOn(courseAssignmentService, 'getAssignments').mockResolvedValue([])
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue([])

    const user = {
      id: 2,
      username: 'leeh',
      email: 'leeh@illinois.edu',
      full_name: 'Dr. Hyoeun Lee',
      role: 'instructor' as const,
      department: 'STAT',
      linked_user_id: 1,
    }
    const authValue: AuthContextValue = {
      session: {
        status: 'authenticated',
        user,
        sessionId: 'foia-instructor-session',
        expiresAt: '2027-05-15T00:00:00Z',
      },
      user,
      login: vi.fn(),
      logout: vi.fn(),
      clearAuthError: vi.fn(),
      isStandaloneFallback: false,
    }

    render(
      <AuthContext.Provider value={authValue}>
        <PreferencesPage />
      </AuthContext.Provider>
    )

    const instructorSelect = screen.getByTestId('instructor-select') as HTMLSelectElement
    expect(instructorSelect).toBeDisabled()
    expect(instructorSelect.value).toBe('1')
    expect(instructorSelect).toHaveTextContent('Dr. Hyoeun Lee — STAT')
    expect(screen.queryByText(/Yugyung Lee/i)).toBeNull()

    await waitFor(() => {
      expect(getInstructorsSpy).toHaveBeenCalled()
    })

    expect(instructorSelect).toBeDisabled()
    expect(instructorSelect.value).toBe('1')
    expect(instructorSelect).toHaveTextContent('Dr. Hyoeun Lee — STAT')
    expect(screen.queryByText(/Yugyung Lee/i)).toBeNull()
  })

  it('selects an assigned course via pill or dropdown, hydrates 2-year habit, filters incompatible slots, saves per-course override, and updates habit badge', async () => {
    vi.spyOn(courseAssignmentService, 'getAssignments').mockResolvedValue([
      {
        id: 1,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        instructor_department: 'BIOE',
        course_id: 3,
        course_code: 'BIOE 205',
        course_name: 'Signals & Systems in Bioengrg',
        department: 'BIOE',
        course_level: 'undergraduate',
      },
      {
        id: 2,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        instructor_department: 'BIOE',
        course_id: 5,
        course_code: 'BIOE 504',
        course_name: 'Analytical Methods in Bioeng',
        department: 'BIOE',
        course_level: 'graduate',
      },
    ])
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue([])
    vi.spyOn(preferenceService, 'getPreferences').mockImplementation(async (filters) => {
      if (filters?.general_only) {
        return [
          {
            id: 50,
            user_id: 1,
            semester_id: 5,
            course_id: null,
            preferred_days: ['F'],
            preferred_slots: ['08:00-09:15'],
            preferred_rooms: [],
            preference_rank: 1,
          },
        ]
      }
      return [
        {
          id: 50,
          user_id: 1,
          semester_id: 5,
          course_id: null,
          preferred_days: ['F'],
          preferred_slots: ['08:00-09:15'],
          preferred_rooms: [],
          preference_rank: 1,
        },
        {
          id: 10,
          user_id: 1,
          semester_id: 5,
          course_id: 3,
          course_code: 'BIOE 205',
          course_name: 'Signals & Systems in Bioengrg',
          preferred_days: ['Tuesday', 'Thursday'],
          preferred_slots: ['11:00-12:15'],
          preferred_rooms: [],
          preference_rank: 2,
        },
      ]
    })
    const submitSpy = vi.spyOn(preferenceService, 'submitPreference').mockResolvedValueOnce({
      id: 10,
      user_id: 1,
      semester_id: 5,
      course_id: 3,
      course_code: 'BIOE 205',
      course_name: 'Signals & Systems in Bioengrg',
      preferred_days: ['M', 'W'],
      preferred_slots: ['09:30-10:45'],
      preferred_rooms: ['RH 204'],
      preference_rank: 1,
    })

    render(<PreferencesPage />)

    const assignedCard = screen.getByTestId('coordinator-assigned-courses')
    await waitFor(() => {
      expect(within(assignedCard).getByTestId('select-course-scope-3')).toBeInTheDocument()
      expect(within(assignedCard).getByTestId('course-habit-badge-3')).toHaveTextContent(
        '2-yr habit: TR 11:00-12:15'
      )
      expect(screen.getByTestId('day-btn-Friday (F)')).toHaveAttribute('aria-pressed', 'true')
    })

    fireEvent.click(within(assignedCard).getByTestId('select-course-scope-3'))

    const courseSelect = screen.getByTestId('preference-course-select') as HTMLSelectElement
    await waitFor(() => {
      expect(courseSelect.value).toBe('3')
      expect(screen.getByText('BIOE 205 Preference')).toBeInTheDocument()
      expect(screen.getByTestId('day-btn-Tuesday (T)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Thursday (R)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Friday (F)')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('slot-11:00-12:15')).toHaveAttribute('aria-pressed', 'true')
    })

    expect(screen.queryByTestId('slot-17:30-18:45')).not.toBeInTheDocument()

    fireEvent.change(courseSelect, { target: { value: '5' } })
    await waitFor(() => {
      expect(screen.getByText('BIOE 504 Preference')).toBeInTheDocument()
      expect(screen.getByTestId('slot-17:30-18:45')).toBeInTheDocument()
    })

    fireEvent.change(courseSelect, { target: { value: '3' } })
    await waitFor(() => {
      expect(screen.getByTestId('slot-11:00-12:15')).toHaveAttribute('aria-pressed', 'true')
    })

    fireEvent.click(screen.getByTestId('day-btn-Tuesday (T)'))
    fireEvent.click(screen.getByTestId('day-btn-Thursday (R)'))
    fireEvent.click(screen.getByTestId('day-btn-Monday (M)'))
    fireEvent.click(screen.getByTestId('day-btn-Wednesday (W)'))
    fireEvent.click(screen.getByTestId('slot-11:00-12:15'))
    fireEvent.click(screen.getByTestId('slot-09:30-10:45'))
    fireEvent.click(screen.getByTestId('room-chip-RH 204'))

    fireEvent.click(screen.getByTestId('save-preferences-button'))

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith({
        user_id: 1,
        semester_id: 5,
        course_id: 3,
        preferred_days: ['M', 'W'],
        preferred_slots: ['09:30-10:45'],
        preferred_rooms: ['RH 204'],
      })
      expect(screen.getByText('Course preferences saved for BIOE 205!')).toBeInTheDocument()
      expect(within(assignedCard).getByTestId('course-habit-badge-3')).toHaveTextContent(
        'Custom pref: MW 09:30-10:45'
      )
    })

    const savedList = screen.getByTestId('saved-preferences-list')
    expect(within(savedList).getByText('General Availability')).toBeInTheDocument()
    expect(within(savedList).getByText('BIOE 205 · Course Preference')).toBeInTheDocument()

    fireEvent.click(within(assignedCard).getByTestId('select-course-scope-general'))
    await waitFor(() => {
      expect(courseSelect.value).toBe('general')
      expect(screen.getByTestId('day-btn-Friday (F)')).toHaveAttribute('aria-pressed', 'true')
    })
  })

  it('supports Load & Edit and Delete on per-course saved preferences', async () => {
    vi.spyOn(courseAssignmentService, 'getAssignments').mockResolvedValue([
      {
        id: 1,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        instructor_department: 'STAT',
        course_id: 400,
        course_code: 'STAT 400',
        course_name: 'Statistics and Probability I',
        department: 'STAT',
        course_level: 'undergraduate',
      },
    ])
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue([])
    vi.spyOn(preferenceService, 'getPreferences').mockImplementation(async (filters) => {
      if (filters?.general_only) return []
      return [
        {
          id: 301,
          user_id: 1,
          semester_id: 5,
          course_id: 400,
          course_code: 'STAT 400',
          course_name: 'Statistics and Probability I',
          preferred_days: ['M', 'W'],
          preferred_slots: ['09:30-10:45'],
          preferred_rooms: ['FH 464'],
          preference_rank: 1,
        },
      ]
    })
    const deleteSpy = vi.spyOn(preferenceService, 'deletePreference').mockResolvedValue()

    render(<PreferencesPage />)

    const savedList = screen.getByTestId('saved-preferences-list')
    const assignedCard = screen.getByTestId('coordinator-assigned-courses')
    await waitFor(() => {
      expect(within(savedList).getByText('STAT 400 · Course Preference')).toBeInTheDocument()
      expect(within(assignedCard).getByTestId('course-habit-badge-400')).toHaveTextContent(
        'Custom pref: MW 09:30-10:45'
      )
    })

    const courseSelect = screen.getByTestId('preference-course-select') as HTMLSelectElement
    expect(courseSelect.value).toBe('general')
    expect(screen.getByTestId('room-chip-FH 464')).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(screen.getByTestId('edit-pref-301'))

    await waitFor(() => {
      expect(courseSelect.value).toBe('400')
      expect(screen.getByText('STAT 400 Preference')).toBeInTheDocument()
      expect(screen.getByTestId('day-btn-Monday (M)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Wednesday (W)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('slot-09:30-10:45')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('room-chip-FH 464')).toHaveAttribute('aria-pressed', 'true')
    })

    fireEvent.click(screen.getByTestId('delete-pref-301'))

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith(301)
      expect(screen.queryByTestId('delete-pref-301')).not.toBeInTheDocument()
      expect(within(assignedCard).getByTestId('course-habit-badge-400')).toHaveTextContent(
        'No preference submitted'
      )
    })
  })

  it('allows Course Coordinators to inspect per-course preferences in read-only mode', async () => {
    setAuthToken(DEMO_COORDINATOR_TOKEN)
    vi.spyOn(courseAssignmentService, 'getAssignments').mockResolvedValue([
      {
        id: 1,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        instructor_department: 'STAT',
        course_id: 400,
        course_code: 'STAT 400',
        course_name: 'Statistics and Probability I',
        department: 'STAT',
        course_level: 'undergraduate',
      },
    ])
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue([])
    vi.spyOn(preferenceService, 'getPreferences').mockImplementation(async (filters) => {
      if (filters?.general_only) {
        return [
          {
            id: 88,
            user_id: 1,
            semester_id: 5,
            course_id: null,
            preferred_days: ['F'],
            preferred_slots: ['08:00-09:15'],
            preferred_rooms: [],
            preference_rank: 1,
          },
        ]
      }
      return [
        {
          id: 88,
          user_id: 1,
          semester_id: 5,
          course_id: null,
          preferred_days: ['F'],
          preferred_slots: ['08:00-09:15'],
          preferred_rooms: [],
          preference_rank: 1,
        },
        {
          id: 89,
          user_id: 1,
          semester_id: 5,
          course_id: 400,
          course_code: 'STAT 400',
          course_name: 'Statistics and Probability I',
          preferred_days: ['T', 'R'],
          preferred_slots: ['11:00-12:15'],
          preferred_rooms: ['RH 204'],
          preference_rank: 1,
        },
      ]
    })

    render(
      <AuthProvider>
        <PreferencesPage />
      </AuthProvider>
    )

    await screen.findByTestId('coordinator-readonly-banner')
    const savedList = screen.getByTestId('saved-preferences-list')
    await waitFor(() => {
      expect(within(savedList).getByText('General Availability')).toBeInTheDocument()
      expect(within(savedList).getByText('STAT 400 · Course Preference')).toBeInTheDocument()
      expect(screen.getByTestId('day-btn-Friday (F)')).toHaveAttribute('aria-pressed', 'true')
    })

    expect(screen.queryByTestId('edit-pref-89')).not.toBeInTheDocument()
    expect(screen.queryByTestId('delete-pref-89')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('select-course-scope-400'))

    await waitFor(() => {
      expect(screen.getByText('STAT 400 Preference')).toBeInTheDocument()
      expect(screen.getByTestId('day-btn-Tuesday (T)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Thursday (R)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Friday (F)')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('slot-11:00-12:15')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('room-chip-RH 204')).toHaveAttribute('aria-pressed', 'true')
    })

    expect(screen.getByTestId('day-btn-Tuesday (T)')).toBeDisabled()
    expect(screen.getByTestId('slot-11:00-12:15')).toBeDisabled()
    expect(screen.getByTestId('room-chip-RH 204')).toBeDisabled()
    expect(screen.queryByTestId('save-preferences-button')).not.toBeInTheDocument()
  })
})
