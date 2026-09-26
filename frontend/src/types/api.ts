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
  instructor_id?: number;
  instructor_name: string;
  room_id?: number;
  room_number: string;
  department?: string;
  day_pattern: string;
  start_time: string;
  end_time: string;
  status: string;
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
  status: 'pending' | 'approved' | 'rejected';
  created_at?: string;
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
