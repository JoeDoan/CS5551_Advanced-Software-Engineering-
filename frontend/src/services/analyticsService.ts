import { apiClient } from './apiClient'

export interface InstructorFairnessStat {
  user_id: number
  instructor_name: string
  department: string
  priority_score: number
  assigned_courses_count: number
  preferred_day_matches: number
  preferred_room_matches: number
  satisfaction_rate: number
}

export interface DepartmentFairnessStat {
  department: string
  instructor_count: number
  total_assigned_courses: number
  average_priority_score: number
  average_satisfaction_rate: number
}

export interface FairnessReport {
  semester_id: number
  total_instructors: number
  total_scheduled_courses: number
  priority_gini_index: number
  workload_gini_index: number
  average_satisfaction_rate: number
  is_demo_fallback?: boolean
  instructors: InstructorFairnessStat[]
  departments: DepartmentFairnessStat[]
}

export interface RoomUtilizationStat {
  room_id: number
  room_number: string
  room_type: string
  capacity: number
  booked_slots_count: number
  total_available_slots: number
  slot_utilization_pct: number
  average_enrollment: number
  seat_occupancy_pct: number
  utilization_tier: 'underutilized' | 'optimal' | 'heavily_booked'
}

export interface RoomUtilizationReport {
  semester_id: number
  total_rooms: number
  total_time_slots: number
  overall_slot_utilization_pct: number
  overall_seat_occupancy_pct: number
  underutilized_rooms_count: number
  heavily_booked_rooms_count: number
  is_demo_fallback?: boolean
  rooms: RoomUtilizationStat[]
}

const FALLBACK_FAIRNESS: FairnessReport = {
  is_demo_fallback: true,
  semester_id: 1,
  total_instructors: 6,
  total_scheduled_courses: 12,
  priority_gini_index: 0.0312,
  workload_gini_index: 0.0,
  average_satisfaction_rate: 91.7,
  instructors: [
    { user_id: 1, instructor_name: 'Dr. Alice Smith', department: 'CS', priority_score: 100000, assigned_courses_count: 2, preferred_day_matches: 2, preferred_room_matches: 2, satisfaction_rate: 100.0 },
    { user_id: 2, instructor_name: 'Dr. Bob Johnson', department: 'CS', priority_score: 110000, assigned_courses_count: 2, preferred_day_matches: 2, preferred_room_matches: 1, satisfaction_rate: 75.0 },
    { user_id: 3, instructor_name: 'Dr. Carol Williams', department: 'ECE', priority_score: 105000, assigned_courses_count: 2, preferred_day_matches: 2, preferred_room_matches: 2, satisfaction_rate: 100.0 },
    { user_id: 4, instructor_name: 'Dr. David Brown', department: 'MATH', priority_score: 115000, assigned_courses_count: 2, preferred_day_matches: 1, preferred_room_matches: 2, satisfaction_rate: 75.0 },
    { user_id: 5, instructor_name: 'Dr. Eva Davis', department: 'CHEM', priority_score: 100000, assigned_courses_count: 2, preferred_day_matches: 2, preferred_room_matches: 2, satisfaction_rate: 100.0 },
    { user_id: 6, instructor_name: 'Dr. Frank Miller', department: 'BIOL', priority_score: 100000, assigned_courses_count: 2, preferred_day_matches: 2, preferred_room_matches: 2, satisfaction_rate: 100.0 },
  ],
  departments: [
    { department: 'CS', instructor_count: 2, total_assigned_courses: 4, average_priority_score: 105000, average_satisfaction_rate: 87.5 },
    { department: 'ECE', instructor_count: 1, total_assigned_courses: 2, average_priority_score: 105000, average_satisfaction_rate: 100.0 },
    { department: 'MATH', instructor_count: 1, total_assigned_courses: 2, average_priority_score: 115000, average_satisfaction_rate: 75.0 },
    { department: 'CHEM', instructor_count: 1, total_assigned_courses: 2, average_priority_score: 100000, average_satisfaction_rate: 100.0 },
    { department: 'BIOL', instructor_count: 1, total_assigned_courses: 2, average_priority_score: 100000, average_satisfaction_rate: 100.0 },
  ],
}

const FALLBACK_UTILIZATION: RoomUtilizationReport = {
  is_demo_fallback: true,
  semester_id: 1,
  total_rooms: 5,
  total_time_slots: 13,
  overall_slot_utilization_pct: 46.15,
  overall_seat_occupancy_pct: 78.4,
  underutilized_rooms_count: 1,
  heavily_booked_rooms_count: 1,
  rooms: [
    { room_id: 1, room_number: 'RH 204', room_type: 'lecture', capacity: 48, booked_slots_count: 6, total_available_slots: 13, slot_utilization_pct: 46.15, average_enrollment: 40, seat_occupancy_pct: 83.33, utilization_tier: 'optimal' },
    { room_id: 2, room_number: 'FH 256', room_type: 'auditorium', capacity: 75, booked_slots_count: 10, total_available_slots: 13, slot_utilization_pct: 76.92, average_enrollment: 62, seat_occupancy_pct: 82.67, utilization_tier: 'heavily_booked' },
    { room_id: 3, room_number: 'FH 464', room_type: 'lab', capacity: 30, booked_slots_count: 5, total_available_slots: 13, slot_utilization_pct: 38.46, average_enrollment: 26, seat_occupancy_pct: 86.67, utilization_tier: 'optimal' },
    { room_id: 4, room_number: 'HH 201', room_type: 'lecture', capacity: 45, booked_slots_count: 7, total_available_slots: 13, slot_utilization_pct: 53.85, average_enrollment: 35, seat_occupancy_pct: 77.78, utilization_tier: 'optimal' },
    { room_id: 5, room_number: 'SCB 205', room_type: 'lab', capacity: 28, booked_slots_count: 2, total_available_slots: 13, slot_utilization_pct: 15.38, average_enrollment: 18, seat_occupancy_pct: 64.29, utilization_tier: 'underutilized' },
  ],
}

export const analyticsService = {
  async getFairnessReport(semesterId = 1): Promise<FairnessReport> {
    try {
      const res = await apiClient.get<FairnessReport>('/analytics/fairness', {
        params: { semester_id: semesterId },
      })
      return res.data
    } catch {
      return { ...FALLBACK_FAIRNESS, semester_id: semesterId }
    }
  },

  async getRoomUtilization(semesterId = 1): Promise<RoomUtilizationReport> {
    try {
      const res = await apiClient.get<RoomUtilizationReport>('/analytics/utilization', {
        params: { semester_id: semesterId },
      })
      return res.data
    } catch {
      return { ...FALLBACK_UTILIZATION, semester_id: semesterId }
    }
  },
}

export default analyticsService
