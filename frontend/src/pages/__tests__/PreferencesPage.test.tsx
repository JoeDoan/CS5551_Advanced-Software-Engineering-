import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PreferencesPage } from '../PreferencesPage'
import { preferenceService } from '../../services/preferenceService'
import { timeSlotService } from '../../services/timeSlotService'

describe('PreferencesPage Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(timeSlotService, 'getTimeSlots').mockResolvedValue([
      { id: 1, day_pattern: 'MW', start_time: '08:00', end_time: '09:15' },
      { id: 2, day_pattern: 'MW', start_time: '09:30', end_time: '10:45' },
      { id: 3, day_pattern: 'MW', start_time: '11:00', end_time: '12:15' },
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
    // Friday is not selected by default
    expect(fridayBtn).toBeInTheDocument()

    // Toggle Friday on
    fireEvent.click(fridayBtn)

    // Toggle Monday off (Monday was selected by default)
    const mondayBtn = screen.getByRole('button', { name: 'Monday (M)' })
    fireEvent.click(mondayBtn)
  })

  it('toggles time slot selection buttons', async () => {
    render(<PreferencesPage />)

    const slotBtn = await screen.findByTestId('slot-09:30-10:45')

    // Initially not active
    expect(slotBtn.className).toContain('bg-slate-50')

    // Click to select
    fireEvent.click(slotBtn)
    expect(slotBtn.className).toContain('bg-blue-50')
    expect(slotBtn.className).toContain('border-blue-600')

    // Click again to deselect
    fireEvent.click(slotBtn)
    expect(slotBtn.className).toContain('bg-slate-50')
  })

  it('displays error toast when submitted without day or time slot', async () => {
    render(<PreferencesPage />)

    // Click Save without selecting any time slot
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

    // Select a time slot (Monday and Wednesday are already selected by default)
    fireEvent.click(await screen.findByTestId('slot-09:30-10:45'))

    // Click Save Preferences
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

    // Select a time slot
    fireEvent.click(await screen.findByTestId('slot-11:00-12:15'))

    // Click Save
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
})
