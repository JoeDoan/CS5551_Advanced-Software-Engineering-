import { describe, it, expect, vi, beforeEach } from 'vitest'
import { exportScheduleToCSV, exportScheduleToJSON } from '../exportSchedule'
import { ScheduleEvent } from '../../types/api'

describe('exportSchedule Utility', () => {
  const sampleEvents: ScheduleEvent[] = [
    {
      id: 1,
      semester_id: 1,
      course_id: 101,
      course_code: 'CS 451',
      course_name: 'Software Engineering II',
      instructor_id: 1,
      instructor_name: 'Dr. Yugyung Lee',
      room_id: 201,
      room_number: 'RH 204',
      department: 'CS',
      day_pattern: 'MWF',
      start_time: '09:00',
      end_time: '09:50',
      status: 'scheduled',
    },
    {
      id: 2,
      semester_id: 1,
      course_id: 102,
      course_code: 'ECE 302',
      course_name: 'Signals & Systems',
      instructor_id: 2,
      instructor_name: 'Dr. Ghulam Rasool',
      room_id: 202,
      room_number: 'FH 256',
      department: 'ECE',
      day_pattern: 'TR',
      start_time: '10:00',
      end_time: '11:15',
      status: 'scheduled',
    },
  ]

  let appendChildSpy: ReturnType<typeof vi.spyOn>
  let removeChildSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node)
    removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node)
  })

  it('exports schedule events to CSV and triggers download', () => {
    let capturedHref = ''
    let capturedDownload = ''
    const clickSpy = vi.fn()

    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = document.createElementNS('http://www.w3.org/1999/xhtml', tagName) as HTMLAnchorElement
      el.setAttribute = (name: string, value: string) => {
        if (name === 'href') capturedHref = value
        if (name === 'download') capturedDownload = value
      }
      el.click = clickSpy
      return el
    })

    exportScheduleToCSV(sampleEvents, 'Fall 2024')

    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(capturedDownload).toBe('UMKC_Schedule_Fall_2024.csv')
    expect(decodeURI(capturedHref)).toContain('Course Code,Course Name,Instructor,Room,Day Pattern,Start Time,End Time,Status')
    expect(decodeURI(capturedHref)).toContain('CS 451,"Software Engineering II","Dr. Yugyung Lee",RH 204,MWF,09:00,09:50,scheduled')
    expect(appendChildSpy).toHaveBeenCalled()
    expect(removeChildSpy).toHaveBeenCalled()
  })

  it('exports schedule events to JSON and triggers download', () => {
    let capturedHref = ''
    let capturedDownload = ''
    const clickSpy = vi.fn()

    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = document.createElementNS('http://www.w3.org/1999/xhtml', tagName) as HTMLAnchorElement
      el.setAttribute = (name: string, value: string) => {
        if (name === 'href') capturedHref = value
        if (name === 'download') capturedDownload = value
      }
      el.click = clickSpy
      return el
    })

    exportScheduleToJSON(sampleEvents, 'Spring 2025')

    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(capturedDownload).toBe('UMKC_Schedule_Spring_2025.json')
    expect(decodeURIComponent(capturedHref)).toContain('"course_code": "CS 451"')
  })
})
