import { ScheduleEvent, CalendarEventItem } from '../types/api'

const DAY_MAP: Record<string, number> = {
  M: 1, // Monday
  T: 2, // Tuesday
  W: 3, // Wednesday
  R: 4, // Thursday
  F: 5, // Friday
}

export const DEPARTMENT_COLORS: Record<string, { bg: string; border: string }> = {
  CS: { bg: '#2563eb', border: '#1d4ed8' },        // Blue
  MATH: { bg: '#7c3aed', border: '#6d28d9' },      // Purple
  ECE: { bg: '#059669', border: '#047857' },       // Emerald
  CHEM: { bg: '#d97706', border: '#b45309' },      // Amber
  BIOL: { bg: '#0d9488', border: '#0f766e' },      // Teal
  'CHEM/BIO': { bg: '#d97706', border: '#b45309' },// Amber
  DEFAULT: { bg: '#004b87', border: '#003866' },   // UMKC Blue
}

export function resolveDepartment(courseCode: string, explicitDept?: string): string {
  if (explicitDept) return explicitDept.toUpperCase()
  const clean = courseCode.trim().toUpperCase()
  if (clean.startsWith('CS') || clean.startsWith('COMP-SCI') || clean.startsWith('CSEE')) return 'CS'
  if (clean.startsWith('MATH') || clean.startsWith('STAT')) return 'MATH'
  if (clean.startsWith('ECE') || clean.startsWith('PHYS')) return 'ECE'
  if (clean.startsWith('CHEM') || clean.startsWith('BIOL')) return 'CHEM/BIO'
  return 'DEFAULT'
}

export function getDepartmentColors(dept: string): { bg: string; border: string } {
  return DEPARTMENT_COLORS[dept] || DEPARTMENT_COLORS.DEFAULT
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
    const dept = resolveDepartment(event.course_code, event.department)
    const colors = getDepartmentColors(dept)

    return {
      id: String(event.id),
      title: `${event.course_code} - ${event.room_number}`,
      start: '',
      end: '',
      daysOfWeek: daysOfWeek.length > 0 ? daysOfWeek : [1],
      startTime: event.start_time,
      endTime: event.end_time,
      backgroundColor: colors.bg,
      borderColor: colors.border,
      textColor: '#ffffff',
      extendedProps: {
        course_code: event.course_code,
        course_name: event.course_name,
        instructor: event.instructor_name,
        room: event.room_number,
        department: dept,
        status: event.status,
      },
    }
  })
}
