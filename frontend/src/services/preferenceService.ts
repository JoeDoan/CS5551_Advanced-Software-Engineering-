import { apiClient, hasHttpStatus } from './apiClient'
import { InstructorPreference, PreferenceFilterParams } from '../types/api'

const MOCK_PREFERENCES: InstructorPreference[] = [
  {
    id: 1,
    user_id: 1,
    semester_id: 1,
    course_id: 1,
    preferred_days: ['Monday', 'Wednesday'],
    preferred_slots: ['09:30-10:45', '11:00-12:15'],
    preferred_rooms: ['RH 204', 'FH 256'],
    preferred_layout: 'lecture',
    preference_rank: 1,
  },
  {
    id: 2,
    user_id: 2,
    semester_id: 1,
    course_id: 2,
    preferred_days: ['Tuesday', 'Thursday'],
    preferred_slots: ['10:00-11:15', '13:00-14:15'],
    preferred_rooms: ['FH 256'],
    preferred_layout: 'auditorium',
    preference_rank: 1,
  },
]

export const preferenceService = {
  /**
   * Fetches preferences filtered by instructor, semester, or course.
   */
  async getPreferences(filters?: PreferenceFilterParams): Promise<InstructorPreference[]> {
    try {
      const params: Record<string, number | boolean> = {}
      if (filters?.user_id !== undefined) params.user_id = filters.user_id
      if (filters?.semester_id !== undefined) params.semester_id = filters.semester_id
      if (filters?.course_id !== undefined) params.course_id = filters.course_id
      if (filters?.general_only !== undefined) params.general_only = filters.general_only

      const response = await apiClient.get<InstructorPreference[]>('/preferences', { params })
      return Array.isArray(response.data) ? response.data : (response.data ?? [])
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      return this._filterMock(filters)
    }
  },

  /**
   * Submits new or revised instructor teaching preferences.
   */
  async submitPreference(payload: InstructorPreference): Promise<InstructorPreference> {
    try {
      const response = await apiClient.post<InstructorPreference>('/preferences', payload)
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const targetCourseId = payload.course_id ?? null
      const existingIdx = MOCK_PREFERENCES.findIndex(
        (p) =>
          p.user_id === payload.user_id &&
          p.semester_id === payload.semester_id &&
          (p.course_id ?? null) === targetCourseId
      )
      if (existingIdx !== -1) {
        const updated: InstructorPreference = {
          ...MOCK_PREFERENCES[existingIdx],
          ...payload,
          course_id: targetCourseId,
          id: MOCK_PREFERENCES[existingIdx].id,
          preference_rank:
            payload.preference_rank ?? MOCK_PREFERENCES[existingIdx].preference_rank ?? 1,
        }
        MOCK_PREFERENCES[existingIdx] = updated
        return updated
      }

      const nextId =
        payload.id ??
        (MOCK_PREFERENCES.length > 0
          ? Math.max(...MOCK_PREFERENCES.map((p) => p.id ?? 0)) + 1
          : 10)
      const simulated: InstructorPreference = {
        ...payload,
        course_id: targetCourseId,
        id: nextId,
        preference_rank: payload.preference_rank || 1,
      }
      MOCK_PREFERENCES.push(simulated)
      return simulated
    }
  },

  async deletePreference(id: number): Promise<void> {
    try {
      await apiClient.delete(`/preferences/${id}`)
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const idx = MOCK_PREFERENCES.findIndex((p) => p.id === id)
      if (idx !== -1) {
        MOCK_PREFERENCES.splice(idx, 1)
      }
    }
  },

  _filterMock(filters?: PreferenceFilterParams): InstructorPreference[] {
    let result = [...MOCK_PREFERENCES]
    if (filters?.user_id !== undefined) {
      result = result.filter((p) => p.user_id === filters.user_id)
    }
    if (filters?.semester_id !== undefined) {
      result = result.filter((p) => p.semester_id === filters.semester_id)
    }
    if (filters?.course_id !== undefined) {
      result = result.filter((p) => p.course_id === filters.course_id)
    }
    if (filters?.general_only) {
      result = result.filter((p) => p.course_id == null)
    }
    return result
  },
}

export default preferenceService
