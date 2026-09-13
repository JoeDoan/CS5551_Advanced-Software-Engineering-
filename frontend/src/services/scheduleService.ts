import { apiClient } from './apiClient'
import { ScheduleEvent } from '../types/api'
import mockScheduleData from '../mocks/scheduleMockData.json'

export const scheduleService = {
  /**
   * Fetches schedules for a semester, falling back to mock data if backend is offline.
   */
  async getSchedules(semesterId: number = 1): Promise<ScheduleEvent[]> {
    try {
      const response = await apiClient.get<ScheduleEvent[]>('/schedules', {
        params: { semester_id: semesterId },
      })
      if (response.data && response.data.length > 0) {
        return response.data
      }
      return mockScheduleData as ScheduleEvent[]
    } catch {
      console.warn('Backend unavailable, using mock schedule data.')
      return mockScheduleData as ScheduleEvent[]
    }
  },
}
