import { apiClient } from './apiClient'
import { Course, CourseFilterParams } from '../types/api'

const MOCK_COURSES: Course[] = [
  { id: 1, course_code: 'CS 101', course_name: 'Problem Solving & Programming I', department: 'CS', credits: 3, expected_enrollment: 45, requires_lab: false },
  { id: 2, course_code: 'CS 201R', course_name: 'Discrete Structures', department: 'CS', credits: 3, expected_enrollment: 40, requires_lab: false },
  { id: 3, course_code: 'CS 303', course_name: 'Data Structures', department: 'CS', credits: 3, expected_enrollment: 50, requires_lab: false },
  { id: 4, course_code: 'CS 441', course_name: 'Programming Languages', department: 'CS', credits: 3, expected_enrollment: 35, requires_lab: false },
  { id: 5, course_code: 'CS 5551', course_name: 'Advanced Software Engineering', department: 'CS', credits: 3, expected_enrollment: 30, requires_lab: false },
  { id: 6, course_code: 'ECE 448', course_name: 'Embedded Systems', department: 'ECE', credits: 3, expected_enrollment: 30, requires_lab: true },
  { id: 7, course_code: 'MATH 110', course_name: 'College Algebra', department: 'MATH', credits: 3, expected_enrollment: 60, requires_lab: false },
  { id: 8, course_code: 'BIOL 108', course_name: 'General Biology I', department: 'CHEM/BIO', credits: 4, expected_enrollment: 55, requires_lab: true },
]

export const courseService = {
  /**
   * Fetches the course catalog with optional department and lab filters.
   */
  async getCourses(filters?: CourseFilterParams): Promise<Course[]> {
    try {
      const params: Record<string, string | boolean> = {}
      if (filters?.department) params.department = filters.department
      if (filters?.requires_lab !== undefined) params.requires_lab = filters.requires_lab

      const response = await apiClient.get<Course[]>('/courses', { params })
      if (response.data && response.data.length > 0) {
        return response.data
      }
      return this._filterMock(filters)
    } catch {
      console.warn('Backend unavailable, using fallback mock courses.')
      return this._filterMock(filters)
    }
  },

  /**
   * Retrieves a single course by ID.
   */
  async getCourseById(id: number): Promise<Course | null> {
    try {
      const response = await apiClient.get<Course>(`/courses/${id}`)
      return response.data
    } catch {
      const found = MOCK_COURSES.find((c) => c.id === id)
      return found || null
    }
  },

  _filterMock(filters?: CourseFilterParams): Course[] {
    let result = [...MOCK_COURSES]
    if (filters?.department) {
      const d = filters.department.toLowerCase()
      result = result.filter((c) => c.department.toLowerCase().includes(d))
    }
    if (filters?.requires_lab !== undefined) {
      result = result.filter((c) => c.requires_lab === filters.requires_lab)
    }
    return result
  },
}

export default courseService
