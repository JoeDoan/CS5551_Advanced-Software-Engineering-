import { apiClient, hasHttpStatus } from './apiClient'
import {
  CourseAssignment,
  CourseAssignmentBulkPayload,
  CourseAssignmentFilterParams,
} from '../types/api'
import { courseService } from './courseService'
import { instructorService } from './instructorService'
import { getCourseLevel } from '../utils/academicDomain'

let mockAssignments: CourseAssignment[] = []
let nextMockAssignmentId = 1

export const resetMockCourseAssignments = (): void => {
  mockAssignments = []
  nextMockAssignmentId = 1
}

export const courseAssignmentService = {
  async getAssignments(filters?: CourseAssignmentFilterParams): Promise<CourseAssignment[]> {
    try {
      const params: Record<string, string | number> = {}
      if (filters?.semester_id !== undefined) params.semester_id = filters.semester_id
      if (filters?.user_id !== undefined) params.user_id = filters.user_id
      if (filters?.department) params.department = filters.department
      if (filters?.level) params.level = filters.level

      const response = await apiClient.get<CourseAssignment[]>('/course-assignments', { params })
      return Array.isArray(response.data) ? response.data : (response.data ?? [])
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      return this._filterMock(filters)
    }
  },

  async setInstructorAssignments(
    payload: CourseAssignmentBulkPayload
  ): Promise<CourseAssignment[]> {
    try {
      const response = await apiClient.put<CourseAssignment[]>('/course-assignments', payload)
      return Array.isArray(response.data) ? response.data : (response.data ?? [])
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const [courses, instructors] = await Promise.all([
        courseService.getCourses(),
        instructorService.getInstructors(),
      ])
      const instructor = instructors.find((i) => i.id === payload.user_id)

      mockAssignments = mockAssignments.filter(
        (a) => !(a.semester_id === payload.semester_id && a.user_id === payload.user_id)
      )

      const uniqueCourseIds = Array.from(new Set(payload.course_ids))
      const created: CourseAssignment[] = uniqueCourseIds.map((courseId) => {
        const course = courses.find((c) => c.id === courseId)
        const courseCode = course?.course_code ?? `COURSE ${courseId}`
        return {
          id: nextMockAssignmentId++,
          semester_id: payload.semester_id,
          user_id: payload.user_id,
          instructor_name: instructor?.full_name ?? `Instructor #${payload.user_id}`,
          instructor_department: instructor?.department ?? '',
          course_id: courseId,
          course_code: courseCode,
          course_name: course?.course_name ?? 'Assigned Course',
          department: course?.department ?? 'CS',
          course_level: getCourseLevel(courseCode),
        }
      })

      mockAssignments.push(...created)
      return created
    }
  },

  async deleteAssignment(id: number): Promise<void> {
    try {
      await apiClient.delete(`/course-assignments/${id}`)
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      mockAssignments = mockAssignments.filter((a) => a.id !== id)
    }
  },

  _filterMock(filters?: CourseAssignmentFilterParams): CourseAssignment[] {
    let result = [...mockAssignments]
    if (filters?.semester_id !== undefined) {
      result = result.filter((a) => a.semester_id === filters.semester_id)
    }
    if (filters?.user_id !== undefined) {
      result = result.filter((a) => a.user_id === filters.user_id)
    }
    if (filters?.department) {
      const targetDept = filters.department.toUpperCase()
      result = result.filter((a) => a.department.toUpperCase() === targetDept)
    }
    if (filters?.level) {
      result = result.filter((a) => a.course_level === filters.level)
    }
    return result
  },
}

export default courseAssignmentService
