import { apiClient } from './apiClient'
import { ScheduleEvent, ScheduleFilterParams } from '../types/api'
import mockScheduleData from '../mocks/scheduleMockData.json'

export const scheduleService = {
  /**
   * Fetches schedules for a given semester with optional filters.
   * Falls back to mock data if the backend server is offline or returns empty.
   */
  async getSchedules(
    semesterId: number = 1,
    filters?: ScheduleFilterParams
  ): Promise<ScheduleEvent[]> {
    try {
      const params: Record<string, string | number> = {
        semester_id: semesterId,
      }
      if (filters?.department) params.department = filters.department
      if (filters?.instructor_id) params.instructor_id = filters.instructor_id
      if (filters?.room_id) params.room_id = filters.room_id

      const response = await apiClient.get<ScheduleEvent[]>('/schedules', { params })

      if (response.data && response.data.length > 0) {
        return response.data
      }
      return this._filterMockData(semesterId, filters)
    } catch {
      console.warn('Backend unavailable or /schedules returned error, using mock schedule data.')
      return this._filterMockData(semesterId, filters)
    }
  },

  /**
   * Retrieves a single schedule event by its ID.
   */
  async getScheduleById(id: number): Promise<ScheduleEvent | null> {
    try {
      const response = await apiClient.get<ScheduleEvent>(`/schedules/${id}`)
      return response.data
    } catch {
      const found = (mockScheduleData as ScheduleEvent[]).find((e) => e.id === id)
      return found || null
    }
  },

  /**
   * Updates an existing schedule assignment (used for drag-and-drop modifications).
   */
  async updateSchedule(
    id: number,
    data: Partial<ScheduleEvent>
  ): Promise<ScheduleEvent> {
    try {
      const response = await apiClient.patch<ScheduleEvent>(`/schedules/${id}`, data)
      return response.data
    } catch {
      console.warn(`Backend offline: simulating update for schedule event ${id}`)
      const existing = (mockScheduleData as ScheduleEvent[]).find((e) => e.id === id)
      if (!existing) {
        throw new Error(`Schedule event with ID ${id} not found`)
      }
      return { ...existing, ...data }
    }
  },

  /**
   * Internal helper to filter mock data by semester and query parameters.
   */
  _filterMockData(
    semesterId: number,
    filters?: ScheduleFilterParams
  ): ScheduleEvent[] {
    let result = (mockScheduleData as ScheduleEvent[]).filter(
      (item) => item.semester_id === semesterId
    )

    if (filters?.department) {
      const targetDept = filters.department.toLowerCase()
      result = result.filter(
        (item) => item.department && item.department.toLowerCase().includes(targetDept)
      )
    }
    if (filters?.instructor_id) {
      result = result.filter((item) => item.instructor_id === filters.instructor_id)
    }
    if (filters?.room_id) {
      result = result.filter((item) => item.room_id === filters.room_id)
    }

    return result
  },
}

export default scheduleService
