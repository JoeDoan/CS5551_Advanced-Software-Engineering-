import { describe, it, expect } from 'vitest'
import { courseService } from '../courseService'

describe('courseService', () => {
  it('retrieves courses catalog list in fallback mode', async () => {
    const courses = await courseService.getCourses()
    expect(courses).toBeDefined()
    expect(courses.length).toBeGreaterThan(0)
    expect(courses[0]).toHaveProperty('course_code')
    expect(courses[0]).toHaveProperty('department')
  })

  it('filters courses by department properly', async () => {
    const csCourses = await courseService.getCourses({ department: 'CS' })
    expect(csCourses.length).toBeGreaterThan(0)
    for (const c of csCourses) {
      expect(c.department).toBe('CS')
    }
  })

  it('filters courses by lab requirement', async () => {
    const labCourses = await courseService.getCourses({ requires_lab: true })
    expect(labCourses.length).toBeGreaterThan(0)
    for (const c of labCourses) {
      expect(c.requires_lab).toBe(true)
    }
  })

  it('retrieves a course by valid ID', async () => {
    const course = await courseService.getCourseById(1)
    expect(course).toBeDefined()
    expect(course?.id).toBe(1)
    expect(course?.course_code).toBe('CS 101')
  })

  it('returns null for an invalid course ID', async () => {
    const course = await courseService.getCourseById(9999)
    expect(course).toBeNull()
  })
})
