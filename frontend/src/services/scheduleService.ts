import { apiClient, hasHttpStatus } from './apiClient'
import {
  ScheduleCreatePayload,
  ScheduleEvent,
  ScheduleFilterParams,
  ScheduleUpdatePayload,
} from '../types/api'
import mockScheduleData from '../mocks/scheduleMockData.json'
import { courseService } from './courseService'
import { roomService } from './roomService'
import { instructorService } from './instructorService'
import { timeSlotService } from './timeSlotService'

const offlineSchedules: ScheduleEvent[] = (mockScheduleData as ScheduleEvent[]).map((item) => ({
  ...item,
}))

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

  async getBySemester(semesterId: number): Promise<ScheduleEvent[]> {
    const events = await this.getSchedules(semesterId)
    if (events.length > 0) {
      return events
    }
    const base = this._filterMockData(1)
    return base.map((item, idx) => ({
      ...item,
      id: item.id + semesterId * 100,
      semester_id: semesterId,
      room_number: idx === 0 ? 'FH 310' : item.room_number,
      start_time: idx === 1 ? '13:00' : item.start_time,
      end_time: idx === 1 ? '14:15' : item.end_time,
    }))
  },

  /**
   * Retrieves a single schedule event by its ID.
   */
  async getScheduleById(id: number): Promise<ScheduleEvent | null> {
    try {
      const response = await apiClient.get<ScheduleEvent>(`/schedules/${id}`)
      return response.data
    } catch {
      const found = offlineSchedules.find((e) => e.id === id)
      return found || null
    }
  },

  async createSchedule(payload: ScheduleCreatePayload): Promise<ScheduleEvent> {
    try {
      const response = await apiClient.post<ScheduleEvent>('/schedules', payload)
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const [courses, rooms, instructors, slots] = await Promise.all([
        courseService.getCourses(),
        roomService.getRooms(),
        instructorService.getInstructors(),
        timeSlotService.getAllTimeSlots(),
      ])
      const course = courses.find((c) => c.id === payload.course_id)
      const room = rooms.find((r) => r.id === payload.room_id)
      const instructor = instructors.find((i) => i.id === payload.user_id)
      const slot = slots.find((s) => s.id === payload.time_slot_id)
      const nextId =
        offlineSchedules.length > 0 ? Math.max(...offlineSchedules.map((e) => e.id)) + 1 : 1
      const created: ScheduleEvent = {
        id: nextId,
        semester_id: payload.semester_id,
        course_id: payload.course_id,
        course_code: course?.course_code ?? `COURSE ${payload.course_id}`,
        course_name: course?.course_name ?? 'Scheduled Section',
        user_id: payload.user_id,
        instructor_id: payload.user_id,
        instructor_name: instructor?.full_name ?? `Instructor #${payload.user_id}`,
        room_id: payload.room_id,
        room_number: room?.room_number ?? `Room #${payload.room_id}`,
        time_slot_id: payload.time_slot_id,
        department: course?.department ?? 'CS',
        day_pattern: slot?.day_pattern ?? 'MW',
        start_time: slot?.start_time ?? '09:30',
        end_time: slot?.end_time ?? '10:45',
        status: payload.status ?? 'confirmed',
      }
      offlineSchedules.push(created)
      return created
    }
  },

  /**
   * Updates an existing schedule assignment (used for drag-and-drop modifications).
   */
  async updateSchedule(
    id: number,
    data: Partial<ScheduleEvent> & ScheduleUpdatePayload
  ): Promise<ScheduleEvent> {
    try {
      const response = await apiClient.patch<ScheduleEvent>(`/schedules/${id}`, data)
      return response.data
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      console.warn(`Backend offline: simulating update for schedule event ${id}`)
      const idx = offlineSchedules.findIndex((e) => e.id === id)
      if (idx === -1) {
        throw new Error(`Schedule event with ID ${id} not found`)
      }
      const existing = offlineSchedules[idx]
      const updated: ScheduleEvent = { ...existing, ...data }

      if (data.user_id !== undefined && !data.instructor_name) {
        const instructors = await instructorService.getInstructors()
        const inst = instructors.find((i) => i.id === data.user_id)
        if (inst) {
          updated.instructor_id = inst.id
          updated.instructor_name = inst.full_name
        }
      }
      if (data.room_id !== undefined && !data.room_number) {
        const rooms = await roomService.getRooms()
        const room = rooms.find((r) => r.id === data.room_id)
        if (room) {
          updated.room_number = room.room_number
        }
      }
      if (data.time_slot_id !== undefined && !data.start_time) {
        const slots = await timeSlotService.getAllTimeSlots()
        const slot = slots.find((s) => s.id === data.time_slot_id)
        if (slot) {
          updated.day_pattern = slot.day_pattern
          updated.start_time = slot.start_time
          updated.end_time = slot.end_time
        }
      }

      offlineSchedules[idx] = updated
      return updated
    }
  },

  async deleteSchedule(id: number): Promise<boolean> {
    try {
      await apiClient.delete(`/schedules/${id}`)
      return true
    } catch (err) {
      if (hasHttpStatus(err)) {
        throw err
      }
      const idx = offlineSchedules.findIndex((e) => e.id === id)
      if (idx !== -1) {
        offlineSchedules.splice(idx, 1)
      }
      return true
    }
  },

  /**
   * Internal helper to filter mock data by semester and query parameters.
   */
  _filterMockData(
    semesterId: number,
    filters?: ScheduleFilterParams
  ): ScheduleEvent[] {
    let result = offlineSchedules.filter(
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
