import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EventDetailModal } from '../EventDetailModal'
import { editRequestService } from '../../../services/editRequestService'
import { ScheduleEvent } from '../../../types/api'

vi.mock('../../../services/editRequestService', () => ({
  editRequestService: {
    createEditRequest: vi.fn(),
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

describe('EventDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders scheduled event metadata when open', () => {
    render(
      <EventDetailModal isOpen={true} event={sampleEvent} onClose={vi.fn()} />
    )

    expect(
      screen.getByText('CS 5551 — Advanced Software Engineering')
    ).toBeInTheDocument()
    expect(screen.getByText('Dr. Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('FH-206')).toBeInTheDocument()
    expect(screen.getByText('09:00 – 10:15')).toBeInTheDocument()
  })

  it('validates empty description and submits edit request on valid input', async () => {
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
})

