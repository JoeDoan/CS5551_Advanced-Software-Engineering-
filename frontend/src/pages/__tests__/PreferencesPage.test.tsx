import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PreferencesPage } from '../PreferencesPage'
import { preferenceService } from '../../services/preferenceService'
import { timeSlotService } from '../../services/timeSlotService'
import { courseService } from '../../services/courseService'
import { roomService } from '../../services/roomService'

describe('PreferencesPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(timeSlotService, 'getTimeSlots').mockResolvedValue([
      { id: 1, day_pattern: 'MW', start_time: '08:00', end_time: '09:15' },
      { id: 2, day_pattern: 'MW', start_time: '09:30', end_time: '10:45' },
      { id: 3, day_pattern: 'MW', start_time: '11:00', end_time: '12:15' },
    ])
    vi.spyOn(courseService, 'getCourses').mockResolvedValue([
      {
        id: 1,
        course_code: 'CS 101',
        course_name: 'Problem Solving & Programming I',
        department: 'CS',
        credits: 3,
        expected_enrollment: 45,
        requires_lab: false,
      },
      {
        id: 5,
        course_code: 'CS 5551',
        course_name: 'Advanced Software Engineering',
        department: 'CS',
        credits: 3,
        expected_enrollment: 30,
        requires_lab: false,
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

  it('renders preference form with instructor selector and default state', () => {
    render(<PreferencesPage />)

    expect(screen.getByText('Instructor Preferences')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Instructor')).toBeInTheDocument()
    expect(screen.getByText('Preferred Days')).toBeInTheDocument()
    expect(screen.getByText('Preferred Time Slots')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save preferences/i })).toBeInTheDocument()
  })

  it('renders time slots from the backend catalog', async () => {
    render(<PreferencesPage />)

    expect(await screen.findByTestId('slot-08:00-09:15')).toHaveTextContent('08:00 - 09:15')
    expect(screen.getByTestId('slot-09:30-10:45')).toBeInTheDocument()
    expect(screen.getByTestId('slot-11:00-12:15')).toBeInTheDocument()
  })

  it('toggles day selection buttons', () => {
    render(<PreferencesPage />)

    const fridayBtn = screen.getByRole('button', { name: 'Friday (F)' })
    expect(fridayBtn).toBeInTheDocument()

    fireEvent.click(fridayBtn)

    const mondayBtn = screen.getByRole('button', { name: 'Monday (M)' })
    fireEvent.click(mondayBtn)
  })

  it('toggles time slot selection buttons', async () => {
    render(<PreferencesPage />)

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

    const saveBtn = screen.getByRole('button', { name: /save preferences/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(
        screen.getByText('Please select at least one teaching day and one time slot.')
      ).toBeInTheDocument()
    })
  })

  it('submits catalog slot keys to API and displays success toast', async () => {
    const submitSpy = vi.spyOn(preferenceService, 'submitPreference').mockResolvedValueOnce({
      id: 101,
      user_id: 1,
      semester_id: 1,
      preferred_days: ['M', 'W'],
      preferred_slots: ['09:30-10:45'],
      preferred_rooms: [],
    })

    render(<PreferencesPage />)

    fireEvent.click(await screen.findByTestId('slot-09:30-10:45'))

    const saveBtn = screen.getByRole('button', { name: /save preferences/i })
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith(
        expect.objectContaining({ preferred_days: ['M', 'W'], preferred_slots: ['09:30-10:45'] })
      )
      expect(screen.getByText('Instructor preferences saved successfully!')).toBeInTheDocument()
    })
  })

  it('handles API submission errors gracefully with error toast', async () => {
    vi.spyOn(preferenceService, 'submitPreference').mockRejectedValueOnce(
      new Error('API failure')
    )

    render(<PreferencesPage />)

    fireEvent.click(await screen.findByTestId('slot-11:00-12:15'))

    const saveBtn = screen.getByRole('button', { name: /save preferences/i })
    fireEvent.click(saveBtn)

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

    const resetBtn = screen.getByRole('button', { name: /reset/i })
    fireEvent.click(resetBtn)

    expect(slotBtn.className).toContain('bg-slate-50')
  })

  it('automatically hydrates saved General preference days, slots, and preferred rooms on page load', async () => {
    vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([
      {
        id: 42,
        user_id: 1,
        semester_id: 1,
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
      expect(screen.getByTestId('day-btn-Tuesday (T)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Thursday (R)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Monday (M)')).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByTestId('day-btn-Wednesday (W)')).toHaveAttribute('aria-pressed', 'false')
      expect(slotBtn.className).toContain('bg-blue-50')
      expect(roomChip).toHaveAttribute('aria-pressed', 'true')
      expect(roomChip.className).toContain('bg-blue-50')
    })
  })

  it('submits course-specific preference scope and preferred classrooms and supports Load & Edit and Delete', async () => {
    vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([])
    const deleteSpy = vi.spyOn(preferenceService, 'deletePreference').mockResolvedValue()
    const submitSpy = vi.spyOn(preferenceService, 'submitPreference').mockResolvedValueOnce({
      id: 205,
      user_id: 1,
      semester_id: 2,
      course_id: 5,
      course_code: 'CS 5551',
      course_name: 'Advanced Software Engineering',
      preferred_days: ['T', 'R'],
      preferred_slots: ['09:30-10:45'],
      preferred_rooms: ['RH 204', 'FH 464'],
    })

    render(<PreferencesPage />)

    await screen.findByTestId('room-chip-RH 204')
    await waitFor(() => {
      expect(screen.getByTestId('preference-course-select').querySelectorAll('option').length).toBe(
        3
      )
    })

    fireEvent.change(screen.getByTestId('preference-semester-select'), {
      target: { value: '2' },
    })
    fireEvent.change(screen.getByTestId('preference-course-select'), {
      target: { value: '5' },
    })
    fireEvent.click(screen.getByTestId('preset-days-tr'))
    fireEvent.click(screen.getByTestId('slot-09:30-10:45'))
    fireEvent.click(screen.getByTestId('room-chip-RH 204'))
    fireEvent.click(screen.getByTestId('room-chip-FH 464'))

    fireEvent.click(screen.getByTestId('save-preferences-button'))

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith({
        user_id: 1,
        semester_id: 2,
        course_id: 5,
        preferred_days: ['T', 'R'],
        preferred_slots: ['09:30-10:45'],
        preferred_rooms: ['RH 204', 'FH 464'],
      })
      expect(screen.getByTestId('edit-pref-205')).toBeInTheDocument()
      expect(screen.getByTestId('delete-pref-205')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('delete-pref-205'))

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith(205)
      expect(screen.queryByTestId('delete-pref-205')).not.toBeInTheDocument()
    })
  })

  it('loads and hydrates a saved course preference via Load & Edit and surfaces domain validation messages', async () => {
    vi.spyOn(preferenceService, 'getPreferences').mockResolvedValue([
      {
        id: 77,
        user_id: 1,
        semester_id: 1,
        course_id: 1,
        course_code: 'CS 101',
        course_name: 'Problem Solving & Programming I',
        preferred_days: ['MWF'],
        preferred_slots: ['08:00-09:15'],
        preferred_rooms: ['FH 464'],
      },
    ])
    vi.spyOn(preferenceService, 'submitPreference').mockRejectedValueOnce(
      new Error('Slot 17:30-18:45 is graduate-only')
    )

    render(<PreferencesPage />)

    const loadEditBtn = await screen.findByTestId('edit-pref-77')
    const slotBtn = await screen.findByTestId('slot-08:00-09:15')
    const labChip = await screen.findByTestId('room-chip-FH 464')

    fireEvent.click(loadEditBtn)

    await waitFor(() => {
      expect((screen.getByTestId('preference-course-select') as HTMLSelectElement).value).toBe('1')
      expect(screen.getByTestId('day-btn-Monday (M)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Wednesday (W)')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('day-btn-Friday (F)')).toHaveAttribute('aria-pressed', 'true')
      expect(slotBtn.className).toContain('bg-blue-50')
      expect(labChip).toHaveAttribute('aria-pressed', 'true')
    })

    fireEvent.click(screen.getByTestId('save-preferences-button'))

    await waitFor(() => {
      expect(screen.getByText('Slot 17:30-18:45 is graduate-only')).toBeInTheDocument()
    })
  })
})
