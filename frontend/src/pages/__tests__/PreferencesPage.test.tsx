import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PreferencesPage } from '../PreferencesPage'
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

  it('locks to active Fall 2026 semester without semester or course preference selectors', () => {
    render(<PreferencesPage />)

    expect(screen.getByText('Instructor Preferences')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Instructor')).toBeInTheDocument()
    expect(screen.getByTestId('active-semester-badge')).toHaveTextContent(
      'Current Term: Fall 2026'
    )
    expect(screen.queryByTestId('preference-course-select')).not.toBeInTheDocument()
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

  it('renders read-only Coordinator-assigned courses with Undergraduate and Graduate badges', async () => {
    vi.spyOn(courseAssignmentService, 'getAssignments').mockResolvedValue([
      {
        id: 1,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Yugyung Lee',
        instructor_department: 'CS',
        course_id: 3,
        course_code: 'CS 303',
        course_name: 'Data Structures',
        department: 'CS',
        course_level: 'undergraduate',
      },
      {
        id: 2,
        semester_id: 5,
        user_id: 1,
        instructor_name: 'Dr. Yugyung Lee',
        instructor_department: 'CS',
        course_id: 5,
        course_code: 'CS 5551',
        course_name: 'Advanced Software Engineering',
        department: 'CS',
        course_level: 'graduate',
      },
    ])
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue([])

    render(<PreferencesPage />)

    const assignedCard = screen.getByTestId('coordinator-assigned-courses')
    await waitFor(() => {
      expect(within(assignedCard).getByText('CS 303')).toBeInTheDocument()
      expect(within(assignedCard).getByText('Undergraduate')).toBeInTheDocument()
      expect(within(assignedCard).getByText('CS 5551')).toBeInTheDocument()
      expect(within(assignedCard).getByText('Graduate')).toBeInTheDocument()
    })
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
})
