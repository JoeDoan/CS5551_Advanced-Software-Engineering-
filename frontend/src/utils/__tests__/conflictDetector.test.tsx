import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { detectScheduleConflicts, compareSemesters } from '../conflictDetector'
import { ConflictInspectorPanel } from '../../components/schedule/ConflictInspectorPanel'
import { SemesterComparisonModal } from '../../components/schedule/SemesterComparisonModal'
import { ScheduleEvent } from '../../types/api'

const cleanEvents: ScheduleEvent[] = [
  {
    id: 1,
    semester_id: 1,
    course_id: 101,
    course_code: 'CS 101',
    course_name: 'Intro to Programming',
    instructor_name: 'Dr. Alice Smith',
    room_number: 'RH 204',
    day_pattern: 'MWF',
    start_time: '09:00',
    end_time: '09:50',
    status: 'confirmed',
  },
  {
    id: 2,
    semester_id: 1,
    course_id: 102,
    course_code: 'CS 201R',
    course_name: 'Discrete Structures',
    instructor_name: 'Dr. Bob Johnson',
    room_number: 'FH 256',
    day_pattern: 'TR',
    start_time: '10:30',
    end_time: '11:45',
    status: 'confirmed',
  },
]

const clashingEvents: ScheduleEvent[] = [
  ...cleanEvents,
  {
    id: 3,
    semester_id: 1,
    course_id: 103,
    course_code: 'CS 303',
    course_name: 'Data Structures',
    instructor_name: 'Dr. Alice Smith',
    room_number: 'RH 204',
    day_pattern: 'MWF',
    start_time: '09:00',
    end_time: '09:50',
    status: 'confirmed',
  },
  {
    id: 4,
    semester_id: 1,
    course_id: 104,
    course_code: 'CS 404',
    course_name: 'Algorithms',
    instructor_name: 'Dr. Alice Smith',
    room_number: 'HH 201',
    day_pattern: 'TR',
    start_time: '14:00',
    end_time: '15:15',
    status: 'confirmed',
  },
]

describe('conflictDetector & Real-Time Constraint Auditor', () => {
  it('certifies conflict-free schedule collapsed by default and shows clean status when expanded', () => {
    const conflicts = detectScheduleConflicts(cleanEvents)
    expect(conflicts).toHaveLength(0)

    render(<ConflictInspectorPanel events={cleanEvents} />)
    expect(screen.getByText('0 Hard Conflicts Certified')).toBeInTheDocument()
    const toggleBtn = screen.getByTestId('toggle-conflict-auditor-btn')
    expect(toggleBtn).toHaveTextContent('View Constraints (0)')
    expect(screen.queryByTestId('conflict-search-input')).not.toBeInTheDocument()

    fireEvent.click(toggleBtn)
    expect(toggleBtn).toHaveTextContent('Hide Constraints')
    expect(screen.getByTestId('conflict-search-input')).toBeInTheDocument()
    expect(
      screen.getByText(/all room, instructor availability, and teaching load constraints are satisfied/i)
    ).toBeInTheDocument()
  })

  it('detects room double-booking, instructor double-booking, and overload with collapsed default and searchable details', () => {
    const conflicts = detectScheduleConflicts(clashingEvents)
    const types = conflicts.map((c) => c.type)
    expect(types).toContain('ROOM_DOUBLE_BOOKING')
    expect(types).toContain('INSTRUCTOR_DOUBLE_BOOKING')
    expect(types).toContain('INSTRUCTOR_OVERLOAD')

    render(<ConflictInspectorPanel events={clashingEvents} />)
    expect(screen.getByText('2 Hard Conflict(s)')).toBeInTheDocument()
    expect(screen.getByText('1 Overload Warning(s)')).toBeInTheDocument()
    expect(screen.queryByTestId('conflict-item-ROOM_DOUBLE_BOOKING')).not.toBeInTheDocument()

    const toggleBtn = screen.getByTestId('toggle-conflict-auditor-btn')
    expect(toggleBtn).toHaveTextContent('View Constraints (3)')
    fireEvent.click(toggleBtn)
    expect(toggleBtn).toHaveTextContent('Hide Constraints')

    expect(screen.getByTestId('conflict-item-ROOM_DOUBLE_BOOKING')).toBeInTheDocument()
    expect(screen.getByTestId('conflict-item-INSTRUCTOR_DOUBLE_BOOKING')).toBeInTheDocument()
    expect(screen.getByTestId('conflict-item-INSTRUCTOR_OVERLOAD')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('conflict-severity-soft'))
    expect(screen.queryByTestId('conflict-item-ROOM_DOUBLE_BOOKING')).not.toBeInTheDocument()
    expect(screen.getByTestId('conflict-item-INSTRUCTOR_OVERLOAD')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('conflict-severity-ALL'))
    const searchInput = screen.getByTestId('conflict-search-input')
    fireEvent.change(searchInput, { target: { value: 'RH 204' } })
    expect(screen.getByTestId('conflict-item-ROOM_DOUBLE_BOOKING')).toBeInTheDocument()
    expect(screen.queryByTestId('conflict-item-INSTRUCTOR_OVERLOAD')).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: 'SCB 999' } })
    expect(
      screen.getByText('No constraints or warnings match your search filter.')
    ).toBeInTheDocument()
  })

  it('computes room and time slot diffs across two semesters and renders comparison modal', () => {
    const sem2Events: ScheduleEvent[] = [
      {
        ...cleanEvents[0],
        room_number: 'FH 310',
      },
      {
        ...cleanEvents[1],
        start_time: '13:00',
        end_time: '14:15',
      },
    ]

    const diff = compareSemesters(cleanEvents, sem2Events)
    expect(diff.roomChangedCourses).toHaveLength(1)
    expect(diff.roomChangedCourses[0].newRoom).toBe('FH 310')
    expect(diff.slotChangedCourses).toHaveLength(1)

    render(
      <SemesterComparisonModal
        isOpen={true}
        onClose={() => {}}
        baseEvents={cleanEvents}
        targetEvents={sem2Events}
      />
    )
    expect(screen.getByText('Multi-Semester Schedule Comparison')).toBeInTheDocument()
    expect(screen.getByText('FH 310')).toBeInTheDocument()
  })
})
