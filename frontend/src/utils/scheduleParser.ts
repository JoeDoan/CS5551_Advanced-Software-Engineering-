import { ScheduleEvent, CalendarEventItem } from '../types/api'

const DAY_MAP: Record<string, number> = {
  M: 1,  // Monday
  T: 2,  // Tuesday
  W: 3,  // Wednesday
  R: 4,  // Thursday
  F: 5,  // Friday
}

export function parseDayPattern(pattern: string): number[] {
  const days: number[] = []
  for (const char of pattern) {
    if (DAY_MAP[char] !== undefined) {
      days.push(DAY_MAP[char])
    }
  }
  return days
}

export function transformToCalendarEvents(events: ScheduleEvent[]): CalendarEventItem[] {
  return events.map((event) => {
    const daysOfWeek = parseDayPattern(event.day_pattern)
    return {
      id: String(event.id),
      title: `${event.course_code} - ${event.room_number}`,
      start: '',
      end: '',
      daysOfWeek: daysOfWeek.length > 0 ? daysOfWeek : [1],
      startTime: event.start_time,
      endTime: event.end_time,
      extendedProps: {
        course_code: event.course_code,
        instructor: event.instructor_name,
        room: event.room_number,
        status: event.status,
      },
    }
  })
}
