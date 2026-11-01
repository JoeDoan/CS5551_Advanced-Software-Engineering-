import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ScheduleFilters } from '../ScheduleFilters'
import { ScheduleTable } from '../ScheduleTable'
import { ScheduleRoomMatrix } from '../ScheduleRoomMatrix'
import { SchedulePage } from '../../../pages/SchedulePage'
import AuthContext, { AuthContextValue } from '../../../context/AuthContext'
import { scheduleService } from '../../../services/scheduleService'
import { ScheduleEvent } from '../../../types/api'

const sampleSchedules: ScheduleEvent[] = [
  {
    id: 1,
    semester_id: 1,
    course_id: 10,
    course_code: 'CS 101',
    course_name: 'Problem Solving & Programming I',
    user_id: 1,
    instructor_id: 1,
    instructor_name: 'Dr. Yugyung Lee',
    room_number: 'RH 204',
    department: 'CS',
    day_pattern: 'MWF',
    start_time: '09:00',
    end_time: '09:50',
    status: 'confirmed',
  },
  {
    id: 2,
    semester_id: 1,
    course_id: 20,
    course_code: 'ECE 216',
    course_name: 'Circuit Theory I',
    user_id: 2,
    instructor_id: 2,
    instructor_name: 'Dr. Praveen Rao',
    room_number: 'FH 256',
    department: 'ECE',
    day_pattern: 'TR',
    start_time: '10:30',
    end_time: '11:45',
    status: 'revised',
  },
]

const makeAuthContext = (
  role: 'coordinator' | 'instructor',
  fullName: string,
  linkedUserId: number | null
): AuthContextValue => {
  const user = {
    id: role === 'coordinator' ? 100 : 101,
    email: `${role}@umkc.edu`,
    username: role,
    full_name: fullName,
    role,
    department: 'CS',
    linked_user_id: linkedUserId,
  }
  return {
    session: {
      status: 'authenticated',
      user,
      sessionId: 'sess-1',
      expiresAt: '2026-12-31T00:00:00Z',
    },
    user,
    login: vi.fn(),
    logout: vi.fn(),
    clearAuthError: vi.fn(),
    isStandaloneFallback: false,
  }
}

describe('ScheduleFilters Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders department selector and search input', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    expect(screen.getByLabelText(/filter by department/i)).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/search by course code, instructor, or room/i)
    ).toBeInTheDocument()
    expect(handleFilterChange).toHaveBeenCalledWith({
      department: 'ALL',
      search: '',
    })
  })

  it('calls onFilterChange when department is changed', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    const select = screen.getByLabelText(/filter by department/i)
    fireEvent.change(select, { target: { value: 'CS' } })

    expect(handleFilterChange).toHaveBeenLastCalledWith({
      department: 'CS',
      search: '',
    })
  })

  it('calls onFilterChange when search input changes', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    const searchInput = screen.getByPlaceholderText(
      /search by course code, instructor, or room/i
    )
    fireEvent.change(searchInput, { target: { value: 'Lee' } })

    expect(handleFilterChange).toHaveBeenLastCalledWith({
      department: 'ALL',
      search: 'Lee',
    })
  })

  it('shows Reset button when filters are active and clears filters on click', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    expect(screen.queryByRole('button', { name: /reset filters/i })).not.toBeInTheDocument()

    const select = screen.getByLabelText(/filter by department/i)
    fireEvent.change(select, { target: { value: 'MATH' } })

    const resetBtn = screen.getByRole('button', { name: /reset filters/i })
    expect(resetBtn).toBeInTheDocument()

    fireEvent.click(resetBtn)

    expect(handleFilterChange).toHaveBeenLastCalledWith({
      department: 'ALL',
      search: '',
    })
    expect(screen.queryByRole('button', { name: /reset filters/i })).not.toBeInTheDocument()
  })

  it('renders instructor and classroom dropdowns when provided and resets all filters together', () => {
    const handleFilterChange = vi.fn()
    const handleInstructorChange = vi.fn()
    const handleRoomChange = vi.fn()

    const { rerender } = render(
      <ScheduleFilters
        onFilterChange={handleFilterChange}
        instructors={['Dr. Praveen Rao', 'Dr. Yugyung Lee']}
        rooms={['FH 256', 'RH 204']}
        selectedInstructor="ALL"
        selectedRoom="ALL"
        onInstructorChange={handleInstructorChange}
        onRoomChange={handleRoomChange}
      />
    )

    const instructorSelect = screen.getByTestId('instructor-filter')
    const roomSelect = screen.getByTestId('room-filter')

    fireEvent.change(instructorSelect, { target: { value: 'Dr. Yugyung Lee' } })
    expect(handleInstructorChange).toHaveBeenCalledWith('Dr. Yugyung Lee')

    fireEvent.change(roomSelect, { target: { value: 'RH 204' } })
    expect(handleRoomChange).toHaveBeenCalledWith('RH 204')

    rerender(
      <ScheduleFilters
        onFilterChange={handleFilterChange}
        instructors={['Dr. Praveen Rao', 'Dr. Yugyung Lee']}
        rooms={['FH 256', 'RH 204']}
        selectedInstructor="Dr. Yugyung Lee"
        selectedRoom="RH 204"
        onInstructorChange={handleInstructorChange}
        onRoomChange={handleRoomChange}
      />
    )

    const resetBtn = screen.getByTestId('reset-filters-button')
    fireEvent.click(resetBtn)
    expect(handleInstructorChange).toHaveBeenLastCalledWith('ALL')
    expect(handleRoomChange).toHaveBeenLastCalledWith('ALL')
  })
})

describe('ScheduleTable, ScheduleRoomMatrix & SchedulePage Views', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('filters ScheduleTable by day-group pills and invokes onSelectEvent', () => {
    const onSelectEvent = vi.fn()
    render(<ScheduleTable events={sampleSchedules} onSelectEvent={onSelectEvent} />)

    expect(screen.getByText('CS 101')).toBeInTheDocument()
    expect(screen.getByText('ECE 216')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('day-group-tr'))
    expect(screen.queryByText('CS 101')).not.toBeInTheDocument()
    expect(screen.getByText('ECE 216')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('schedule-row-details-2'))
    expect(onSelectEvent).toHaveBeenCalledWith(sampleSchedules[1])
  })

  it('renders ScheduleRoomMatrix with Open indicators and clickable course chips', () => {
    const onSelectEvent = vi.fn()
    render(
      <ScheduleRoomMatrix
        events={sampleSchedules}
        rooms={['FH 256', 'RH 204']}
        onSelectEvent={onSelectEvent}
      />
    )

    expect(screen.getAllByText('Open').length).toBeGreaterThan(0)
    const chip = screen.getByTestId('matrix-event-chip-1')
    expect(chip).toHaveTextContent('CS 101')
    expect(chip).toHaveTextContent('Lee')

    fireEvent.click(chip)
    expect(onSelectEvent).toHaveBeenCalledWith(sampleSchedules[0])
  })

  it('defaults Coordinator to Table View and switches views without refetching schedules', async () => {
    const getSchedulesSpy = vi
      .spyOn(scheduleService, 'getSchedules')
      .mockResolvedValue(sampleSchedules)

    render(
      <MemoryRouter>
        <AuthContext.Provider value={makeAuthContext('coordinator', 'Course Coordinator', null)}>
          <SchedulePage />
        </AuthContext.Provider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('schedule-section-count')).toHaveTextContent(
        'Showing 2 of 2 sections'
      )
    })
    expect(screen.getByTestId('schedule-table-view')).toBeInTheDocument()
    expect(getSchedulesSpy).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByTestId('view-mode-matrix'))
    expect(screen.getByTestId('schedule-room-matrix-view')).toBeInTheDocument()
    expect(getSchedulesSpy).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByTestId('view-mode-calendar'))
    expect(screen.getByTestId('schedule-calendar-view')).toBeInTheDocument()
    expect(getSchedulesSpy).toHaveBeenCalledTimes(1)
  })

  it('defaults Instructor to My Teaching Schedule in Weekly Calendar with 1-click toggle to All Department Schedule', async () => {
    vi.spyOn(scheduleService, 'getSchedules').mockResolvedValue(sampleSchedules)

    render(
      <MemoryRouter>
        <AuthContext.Provider value={makeAuthContext('instructor', 'Dr. Yugyung Lee', 1)}>
          <SchedulePage />
        </AuthContext.Provider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('schedule-section-count')).toHaveTextContent(
        'Showing 1 of 2 sections'
      )
    })
    expect(screen.getByTestId('schedule-calendar-view')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('schedule-scope-all'))
    expect(screen.getByTestId('schedule-section-count')).toHaveTextContent(
      'Showing 2 of 2 sections'
    )
  })

  it('colors STAT, PHYS, and BIOE chips distinctly and ranks MR rows ahead of single-day rows in ScheduleRoomMatrix', () => {
    const uiucEvents: ScheduleEvent[] = [
      {
        id: 11,
        semester_id: 5,
        course_id: 101,
        course_code: 'PHYS 211',
        course_name: 'University Physics: Mechanics',
        user_id: 3,
        instructor_id: 3,
        instructor_name: 'Dr. Mats Selen',
        room_number: 'LL 141',
        department: 'PHYS',
        day_pattern: 'M',
        start_time: '09:00',
        end_time: '09:50',
        status: 'confirmed',
      },
      {
        id: 12,
        semester_id: 5,
        course_id: 102,
        course_code: 'STAT 400',
        course_name: 'Statistics and Probability I',
        user_id: 1,
        instructor_id: 1,
        instructor_name: 'Dr. Hyoeun Lee',
        room_number: 'DCL 1320',
        department: 'STAT',
        day_pattern: 'MR',
        start_time: '11:00',
        end_time: '12:15',
        status: 'confirmed',
      },
      {
        id: 13,
        semester_id: 5,
        course_id: 103,
        course_code: 'BIOE 205',
        course_name: 'Signals & Systems in Bioengrg',
        user_id: 4,
        instructor_id: 4,
        instructor_name: 'Dr. Brad Sutton',
        room_number: 'CIF 3031',
        department: 'BIOE',
        day_pattern: 'MF',
        start_time: '10:00',
        end_time: '11:15',
        status: 'confirmed',
      },
    ]

    render(<ScheduleRoomMatrix events={uiucEvents} onSelectEvent={vi.fn()} />)

    expect(screen.getByTestId('matrix-event-chip-12')).toHaveStyle({
      backgroundColor: '#7c3aed',
    })
    expect(screen.getByTestId('matrix-event-chip-11')).toHaveStyle({
      backgroundColor: '#059669',
    })
    expect(screen.getByTestId('matrix-event-chip-13')).toHaveStyle({
      backgroundColor: '#0d9488',
    })

    const bodyRows = screen.getAllByRole('row').slice(1)
    expect(bodyRows[0]).toHaveTextContent('MF')
    expect(bodyRows[1]).toHaveTextContent('MR')
    expect(bodyRows[2]).toHaveTextContent('M')
  })
})
