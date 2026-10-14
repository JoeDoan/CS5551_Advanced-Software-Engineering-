import { ScheduleEvent } from '../types/api'

export function exportScheduleToCSV(events: ScheduleEvent[], semesterName: string): void {
  const headers = [
    'Course Code',
    'Course Name',
    'Instructor',
    'Room',
    'Day Pattern',
    'Start Time',
    'End Time',
    'Status',
  ]
  const rows = events.map((e) => [
    e.course_code || '',
    `"${(e.course_name || '').replace(/"/g, '""')}"`,
    `"${(e.instructor_name || '').replace(/"/g, '""')}"`,
    e.room_number || '',
    e.day_pattern || '',
    e.start_time || '',
    e.end_time || '',
    e.status || '',
  ])

  const csvContent =
    'data:text/csv;charset=utf-8,' +
    [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute(
    'download',
    `UMKC_Schedule_${semesterName.replace(/\s+/g, '_')}.csv`
  )
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function exportScheduleToJSON(events: ScheduleEvent[], semesterName: string): void {
  const jsonContent =
    'data:application/json;charset=utf-8,' +
    encodeURIComponent(JSON.stringify(events, null, 2))
  const link = document.createElement('a')
  link.setAttribute('href', jsonContent)
  link.setAttribute(
    'download',
    `UMKC_Schedule_${semesterName.replace(/\s+/g, '_')}.json`
  )
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
