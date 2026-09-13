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
}

export interface InstructorPreference {
  id?: number;
  user_id: number;
  semester_id: number;
  course_id?: number;
  preferred_days: string[];
  preferred_slots: string[];
  preferred_rooms: string[];
  preference_rank?: number;
}

export interface ScheduleEvent {
  id: number;
  semester_id: number;
  course_id: number;
  course_code: string;
  course_name: string;
  instructor_name: string;
  room_number: string;
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
  extendedProps: {
    course_code: string;
    instructor: string;
    room: string;
    status: string;
  };
}
