import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { EventDetailModal } from '../EventDetailModal'
import AuthContext, { AuthContextValue } from '../../../context/AuthContext'
import { editRequestService } from '../../../services/editRequestService'
import { roomService } from '../../../services/roomService'
import { timeSlotService } from '../../../services/timeSlotService'
import { ScheduleEvent } from '../../../types/api'

vi.mock('../../../services/editRequestService', () => ({
  editRequestService: {
    createEditRequest: vi.fn(),
  },
}))

vi.mock('../../../services/roomService', () => ({
  roomService: {
    getRooms: vi.fn(),
  },
}))

vi.mock('../../../services/timeSlotService', () => ({
  timeSlotService: {
    getTimeSlots: vi.fn(),
    getAllTimeSlots: vi.fn(),
  },
}))

const sampleEvent: ScheduleEvent = {
  id: 12,
  semester_id: 1,
  course_id: 101,
  course_code: 'CS 5551',
  course_name: 'Advanced Software Engineering',
  instructor_name: 'Dr. Alice Smith',
  room_number: 'FH-206',
  department: 'CS',
  day_pattern: 'TR',
  start_time: '09:00',
  end_time: '10:15',
  status: 'confirmed',
}

const makeAuthValue = (
  role: 'coordinator' | 'instructor',
  fullName: string,
  linkedUserId: number | null
): AuthContextValue => {
  const user = {
    id: role === 'coordinator' ? 100 : 105,
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
      sessionId: 'sess-modal',
      expiresAt: '2026-12-31T00:00:00Z',
    },
    user,
    login: vi.fn(),
    logout: vi.fn(),
    clearAuthError: vi.fn(),
    isStandaloneFallback: false,
  }
}

describe('EventDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(roomService.getRooms).mockResolvedValue([
      {
        id: 4,
        room_number: 'FH 310',
        capacity: 35,
        room_type: 'seminar',
        building_id: 2,
      },
    ])
    const mockSlots = [
      {
        id: 8,
        day_pattern: 'TR',
        start_time: '13:00',
        end_time: '14:15',
      },
    ]
    vi.mocked(timeSlotService.getTimeSlots).mockResolvedValue(mockSlots)
    vi.mocked(timeSlotService.getAllTimeSlots).mockResolvedValue(mockSlots)
  })

  it('renders scheduled event metadata when open without exposing raw numeric requester ID input', async () => {
    render(
      <EventDetailModal isOpen={true} event={sampleEvent} onClose={vi.fn()} />
    )

    expect(
      screen.getByText('CS 5551 — Advanced Software Engineering')
    ).toBeInTheDocument()
    expect(screen.getByText('Dr. Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('FH-206')).toBeInTheDocument()
    expect(screen.getByText('09:00 – 10:15')).toBeInTheDocument()
    expect(document.getElementById('edit-requester-id')).toBeNull()

    await waitFor(() => {
      expect(roomService.getRooms).toHaveBeenCalled()
    })
  })

  it('validates empty description and submits edit request on valid input without optional keys when unselected', async () => {
    vi.mocked(editRequestService.createEditRequest).mockResolvedValue({
      id: 77,
      schedule_id: 12,
      requester_id: 1,
      requested_changes: 'Need larger lab room FH-310',
      status: 'pending',
    })

    render(
      <EventDetailModal isOpen={true} event={sampleEvent} onClose={vi.fn()} />
    )

    fireEvent.click(screen.getByTestId('submit-edit-request-button'))
    expect(
      screen.getByText('Please describe the requested schedule change.')
    ).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('edit-request-textarea'), {
      target: { value: 'Need larger lab room FH-310' },
    })
    fireEvent.click(screen.getByTestId('submit-edit-request-button'))

    await waitFor(() => {
      expect(editRequestService.createEditRequest).toHaveBeenCalledWith({
        schedule_id: 12,
        requester_id: 1,
        requested_changes: 'Need larger lab room FH-310',
      })
    })
    expect(screen.getByText('Edit Request Queued')).toBeInTheDocument()
  })

  it('binds logged-in instructor linked_user_id and includes proposed_room_id and proposed_time_slot_id when selected', async () => {
    vi.mocked(editRequestService.createEditRequest).mockResolvedValue({
      id: 88,
      schedule_id: 12,
      requester_id: 7,
      requested_changes: 'Move to FH 310 afternoon slot',
      proposed_room_id: 4,
      proposed_time_slot_id: 8,
      status: 'pending',
    })

    render(
      <AuthContext.Provider value={makeAuthValue('instructor', 'Dr. Alice Smith', 7)}>
        <EventDetailModal isOpen={true} event={sampleEvent} onClose={vi.fn()} />
      </AuthContext.Provider>
    )

    expect(screen.getByTestId('requester-identity')).toHaveTextContent(
      'Requester: Dr. Alice Smith'
    )

    await waitFor(() => {
      expect(screen.getByText(/FH 310/)).toBeInTheDocument()
      expect(screen.getByText(/TR 13:00 – 14:15/)).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('proposed-room-select'), {
      target: { value: '4' },
    })
    fireEvent.change(screen.getByTestId('proposed-slot-select'), {
      target: { value: '8' },
    })
    fireEvent.change(screen.getByTestId('edit-request-textarea'), {
      target: { value: 'Move to FH 310 afternoon slot' },
    })
    fireEvent.click(screen.getByTestId('submit-edit-request-button'))

    await waitFor(() => {
      expect(editRequestService.createEditRequest).toHaveBeenCalledWith({
        schedule_id: 12,
        requester_id: 7,
        requested_changes: 'Move to FH 310 afternoon slot',
        proposed_room_id: 4,
        proposed_time_slot_id: 8,
      })
    })
  })

  it('renders Coordinator Section Controls with direct link to /courses instead of self-request form', () => {
    render(
      <MemoryRouter>
        <AuthContext.Provider value={makeAuthValue('coordinator', 'Course Coordinator', null)}>
          <EventDetailModal isOpen={true} event={sampleEvent} onClose={vi.fn()} />
        </AuthContext.Provider>
      </MemoryRouter>
    )

    expect(screen.getByTestId('coordinator-section-controls')).toBeInTheDocument()
    expect(screen.queryByTestId('submit-edit-request-button')).not.toBeInTheDocument()

    const manageLink = screen.getByTestId('manage-sections-link')
    expect(manageLink).toHaveTextContent('Manage in Scheduled Sections')
    expect(manageLink).toHaveAttribute('href', '/courses')
  })
})
