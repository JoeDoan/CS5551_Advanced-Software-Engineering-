import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ScheduleCalendar } from '../ScheduleCalendar'
import { scheduleService } from '../../../services/scheduleService'

describe('ScheduleCalendar Component', () => {
  it('mounts and renders calendar header and department legend', async () => {
    const { container } = render(<ScheduleCalendar semesterId={1} />)

    expect(screen.getByText('Weekly Schedule Matrix')).toBeInTheDocument()
    expect(screen.getByText('Computer Science')).toBeInTheDocument()
    expect(screen.getByText('Mathematics')).toBeInTheDocument()
    expect(screen.getByText('ECE / Physics')).toBeInTheDocument()
    expect(screen.getByText('Chemistry / Biology')).toBeInTheDocument()

    // Verify FullCalendar mounts its timeGrid view and weekday columns
    await waitFor(() => {
      const calendarView = container.querySelector('.fc-timeGridWeek-view')
      expect(calendarView).toBeInTheDocument()

      const monHeader = container.querySelector('.fc-day-mon')
      const friHeader = container.querySelector('.fc-day-fri')
      expect(monHeader).toBeInTheDocument()
      expect(friHeader).toBeInTheDocument()
    })
  })

  it('handles service error gracefully when schedule fetching fails', async () => {
    vi.spyOn(scheduleService, 'getSchedules').mockRejectedValueOnce(new Error('Network error'))
    const { container } = render(<ScheduleCalendar semesterId={999} />)

    await waitFor(() => {
      const calendarView = container.querySelector('.fc-timeGridWeek-view')
      expect(calendarView).toBeInTheDocument()
    })

    // Ensures component does not crash and finishes loading
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })
})
