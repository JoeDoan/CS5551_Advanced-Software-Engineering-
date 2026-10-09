import { describe, it, expect } from 'vitest'
import { scheduleService } from '../scheduleService'

describe('scheduleService', () => {
  it('returns schedule events for a requested semester', async () => {
    const events = await scheduleService.getSchedules(1)
    expect(events).toBeDefined()
    expect(events.length).toBeGreaterThan(0)
    expect(events[0]).toHaveProperty('course_code')
    expect(events[0]).toHaveProperty('room_number')
    expect(events[0]).toHaveProperty('day_pattern')
  })

  it('filters schedule events by department properly in fallback mode', async () => {
    const csEvents = await scheduleService.getSchedules(1, { department: 'CS' })
    expect(csEvents.length).toBeGreaterThan(0)
    for (const evt of csEvents) {
      expect(evt.department).toBe('CS')
    }
  })

  it('finds single schedule event by id', async () => {
    const event = await scheduleService.getScheduleById(1)
    expect(event).toBeDefined()
    expect(event?.id).toBe(1)
    expect(event?.course_code).toBe('CS 101')
  })

  it('updates schedule event assignment in simulated environment', async () => {
    const updated = await scheduleService.updateSchedule(1, {
      room_number: 'FH 256',
      room_id: 5,
    })
    expect(updated.id).toBe(1)
    expect(updated.room_number).toBe('FH 256')
    expect(updated.room_id).toBe(5)
  })
})
