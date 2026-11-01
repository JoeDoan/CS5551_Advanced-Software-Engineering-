import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  ACADEMIC_SEMESTERS,
  CURRENT_SEMESTER_ID,
  CURRENT_SEMESTER_NAME,
  STANDARD_DEPARTMENTS,
  formatCourseLevel,
  formatRoomWithBuilding,
  getCourseLevel,
  resolveBuildingName,
} from '../academicDomain'
import {
  courseAssignmentService,
  resetMockCourseAssignments,
} from '../../services/courseAssignmentService'
import { apiClient, ApiError } from '../../services/apiClient'

describe('academicDomain & courseAssignmentService', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    resetMockCourseAssignments()
  })

  it('identifies active semester as Fall 2025 (id 5) across the 6-semester registry and includes BIOE', () => {
    expect(CURRENT_SEMESTER_ID).toBe(5)
    expect(CURRENT_SEMESTER_NAME).toBe('Fall 2025')
    const active = ACADEMIC_SEMESTERS.filter((s) => s.isActive)
    expect(active).toEqual([{ id: 5, name: 'Fall 2025', isActive: true }])
    expect(ACADEMIC_SEMESTERS.map((s) => s.name)).toEqual([
      'Fall 2023',
      'Spring 2024',
      'Fall 2024',
      'Spring 2025',
      'Fall 2025',
      'Spring 2026',
    ])
    expect(STANDARD_DEPARTMENTS).toContain('BIOE')
  })

  it('classifies undergraduate and graduate course codes for 3-digit and 4-digit numbering', () => {
    expect(getCourseLevel('CS 101')).toBe('undergraduate')
    expect(getCourseLevel('CS 303')).toBe('undergraduate')
    expect(getCourseLevel('ECE 4990')).toBe('undergraduate')
    expect(getCourseLevel('MATH 510')).toBe('graduate')
    expect(getCourseLevel('CS 5551')).toBe('graduate')
    expect(getCourseLevel('CS 5560')).toBe('graduate')
    expect(formatCourseLevel('undergraduate')).toBe('Undergraduate')
    expect(formatCourseLevel('graduate')).toBe('Graduate')
  })

  it('resolves UMKC and UIUC building names from explicit fields, building codes, or room number prefixes', () => {
    expect(
      resolveBuildingName({
        room_number: 'FH 206',
        building_name: 'Flarsheim Science Center',
      })
    ).toBe('Flarsheim Science Center')

    expect(
      resolveBuildingName({
        room_number: '101',
        building_code: 'scb',
      })
    ).toBe('Spencer Chemistry Building')

    expect(
      formatRoomWithBuilding({
        room_number: 'RH 204',
      })
    ).toBe('RH 204 — Royall Hall')

    expect(
      formatRoomWithBuilding({
        room_number: 'SC 1404',
      })
    ).toBe('SC 1404 — Siebel Center for Computer Science')

    expect(
      resolveBuildingName({
        room_number: 'ECEB 1002',
      })
    ).toBe('Electrical & Computer Engineering Building')

    expect(
      resolveBuildingName({
        room_number: 'DCL 1320',
      })
    ).toBe('Digital Computer Laboratory')

    expect(
      resolveBuildingName({
        room_number: 'CIF 3031',
      })
    ).toBe('Campus Instructional Facility')

    expect(
      formatRoomWithBuilding({
        room_number: 'XYZ 999',
      })
    ).toBe('XYZ 999')
  })

  it('persists, filters, and deletes offline faculty course assignments while rethrowing HTTP errors', async () => {
    const saved = await courseAssignmentService.setInstructorAssignments({
      semester_id: 5,
      user_id: 1,
      course_ids: [3, 5],
    })
    expect(saved).toHaveLength(2)

    const gradOnly = await courseAssignmentService.getAssignments({
      semester_id: 5,
      department: 'CS',
      level: 'graduate',
    })
    expect(gradOnly).toHaveLength(1)
    expect(gradOnly[0].course_code).toBe('CS 5551')

    await courseAssignmentService.deleteAssignment(gradOnly[0].id)
    const remaining = await courseAssignmentService.getAssignments({
      semester_id: 5,
      user_id: 1,
    })
    expect(remaining).toHaveLength(1)
    expect(remaining[0].course_code).toBe('CS 303')

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new ApiError('Validation failed', 422))
    await expect(
      courseAssignmentService.setInstructorAssignments({
        semester_id: 5,
        user_id: 1,
        course_ids: [999],
      })
    ).rejects.toThrow('Validation failed')
  })
})
