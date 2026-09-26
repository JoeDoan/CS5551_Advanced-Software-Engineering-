import { apiClient } from './apiClient'
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
      const params: Record<string, number> = {}
      if (filters?.user_id) params.user_id = filters.user_id
      if (filters?.semester_id) params.semester_id = filters.semester_id
      if (filters?.course_id) params.course_id = filters.course_id

      const response = await apiClient.get<InstructorPreference[]>('/preferences', { params })
      if (response.data && response.data.length > 0) {
        return response.data
      }
      return this._filterMock(filters)
    } catch {
      console.warn('Backend unavailable, using fallback mock preferences.')
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
    } catch {
      console.warn('Backend unavailable, simulating preference submission.')
      const simulated: InstructorPreference = {
        ...payload,
        id: payload.id || Math.floor(Math.random() * 1000) + 10,
        preference_rank: payload.preference_rank || 1,
      }
      MOCK_PREFERENCES.push(simulated)
      return simulated
    }
  },

  _filterMock(filters?: PreferenceFilterParams): InstructorPreference[] {
    let result = [...MOCK_PREFERENCES]
    if (filters?.user_id) {
      result = result.filter((p) => p.user_id === filters.user_id)
    }
    if (filters?.semester_id) {
      result = result.filter((p) => p.semester_id === filters.semester_id)
    }
    if (filters?.course_id) {
      result = result.filter((p) => p.course_id === filters.course_id)
    }
    return result
  },
}

export default preferenceService
