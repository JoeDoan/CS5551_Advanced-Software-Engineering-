export interface Course {
  id: number;
  course_code: string;
  course_name: string;
  department: string;
  credits: number;
  expected_enrollment: number;
  requires_lab: boolean;
}

export interface Room {
  id: number;
  room_number: string;
  capacity: number;
  room_type: string;
  building_id: number;
  building_code?: string;
  building_name?: string;
}

export interface InstructorPreference {
  id?: number;
  user_id: number;
  semester_id: number;
  course_id?: number;
  preferred_days: string[];
  preferred_slots: string[];
  preferred_rooms: string[];
  preferred_layout?: string;
  preference_rank?: number;
}

export interface ScheduleEvent {
  id: number;
  semester_id: number;
  course_id: number;
  course_code: string;
  course_name: string;
  user_id?: number;
  instructor_id?: number;
  instructor_name: string;
  room_id?: number;
  room_number: string;
  time_slot_id?: number;
  department?: string;
  day_pattern: string;
  start_time: string;
  end_time: string;
  status: string;
}

export interface ScheduleCreatePayload {
  semester_id: number;
  course_id: number;
  user_id: number;
  room_id: number;
  time_slot_id: number;
  status?: string;
}

export interface ScheduleUpdatePayload {
  room_id?: number;
  time_slot_id?: number;
  user_id?: number;
  status?: string;
  room_number?: string;
}

export interface CalendarEventItem {
  id: string;
  title: string;
  start: string;
  end: string;
  daysOfWeek?: number[];
  startTime?: string;
  endTime?: string;
  backgroundColor?: string;
  borderColor?: string;
  textColor?: string;
  extendedProps: {
    course_code: string;
    course_name?: string;
    instructor: string;
    room: string;
    department?: string;
    status: string;
  };
}

export interface ScheduleFilterParams {
  semester_id?: number;
  department?: string;
  instructor_id?: number;
  room_id?: number;
}

export interface CourseFilterParams {
  department?: string;
  requires_lab?: boolean;
}

export interface RoomFilterParams {
  min_capacity?: number;
  building_id?: number;
  room_type?: string;
}

export interface PreferenceFilterParams {
  user_id?: number;
  semester_id?: number;
  course_id?: number;
}

export interface TimeSlot {
  id: number;
  day_pattern: string;
  start_time: string;
  end_time: string;
  slot_label?: string | null;
  pattern_type?: string;
  level?: string | null;
}

export interface Building {
  id: number;
  campus_id: number;
  name: string;
  code: string;
}

export interface Campus {
  id: number;
  name: string;
  code: string;
  address?: string;
}

export interface Semester {
  id: number;
  semester_id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: 'admin' | 'coordinator' | 'instructor';
  department: string;
  priority_score: number;
}

export interface EditRequest {
  id: number;
  schedule_id: number;
  requester_id: number;
  requested_changes: string;
  proposed_room_id?: number | null;
  proposed_time_slot_id?: number | null;
  reviewer_notes?: string | null;
  status: 'pending' | 'approved' | 'rejected';
  created_at?: string;
}

export interface EditRequestCreatePayload {
  schedule_id: number;
  requester_id: number;
  requested_changes: string;
  proposed_room_id?: number;
  proposed_time_slot_id?: number;
}

export interface EditRequestReviewPayload {
  status: 'approved' | 'rejected';
  reviewer_notes?: string;
}

export interface InstructorPriorityStat {
  user_id: number;
  instructor_name: string;
  old_priority: number;
  new_priority: number;
  delta: number;
  satisfaction_rate?: number | null;
}

export interface SimulationResult {
  semesters_simulated: number;
  total_scheduled_events: number;
  average_satisfaction_rate: number;
  total_wall_time_seconds: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ApiErrorResponse {
  message: string;
  detail?: string | Array<{ loc?: string[]; msg?: string; type?: string }>;
  status?: number;
}

export type AuthRole = 'coordinator' | 'instructor';

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: AuthRole;
  department: string;
  linked_user_id: number | null;
}

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  session_id: string;
  expires_at: string;
  user: AuthUser;
}

export interface SessionVerifyResponse {
  session_id: string;
  expires_at: string;
  user: AuthUser;
}

export interface LogoutResponse {
  status: 'logged_out';
  revoked_session_id: string;
}

export interface InstructorSummary {
  id: number;
  full_name: string;
  email: string;
  department: string;
  priority_score: number;
}

