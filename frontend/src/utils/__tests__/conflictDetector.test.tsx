import { render, screen } from '@testing-library/react'
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

describe('conflictDetector & Sprint 3 Schedule Inspector', () => {
  it('certifies conflict-free schedule when rooms and slots are distinct', () => {
    const conflicts = detectScheduleConflicts(cleanEvents)
    expect(conflicts).toHaveLength(0)

    render(<ConflictInspectorPanel events={cleanEvents} />)
    expect(screen.getByText('0 Hard Conflicts Certified')).toBeInTheDocument()
  })

  it('detects room double-booking, instructor double-booking, and overload', () => {
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

    const conflicts = detectScheduleConflicts(clashingEvents)
    const types = conflicts.map((c) => c.type)
    expect(types).toContain('ROOM_DOUBLE_BOOKING')
    expect(types).toContain('INSTRUCTOR_DOUBLE_BOOKING')
    expect(types).toContain('INSTRUCTOR_OVERLOAD')

    render(<ConflictInspectorPanel events={clashingEvents} />)
    expect(screen.getByText('2 Hard Conflict(s)')).toBeInTheDocument()
    expect(screen.getByText('1 Overload Warning(s)')).toBeInTheDocument()
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
