import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '../apiClient'
import { timeSlotService } from '../timeSlotService'

describe('timeSlotService', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('dedupes catalog rows that share a time range across day patterns', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      data: [
        { id: 2, day_pattern: 'TR', start_time: '09:30', end_time: '10:45' },
        { id: 1, day_pattern: 'MW', start_time: '08:00', end_time: '09:15' },
        { id: 3, day_pattern: 'MW', start_time: '09:30', end_time: '10:45' },
      ],
    })

    const slots = await timeSlotService.getTimeSlots()

    expect(slots.map((s) => `${s.start_time}-${s.end_time}`)).toEqual(['08:00-09:15', '09:30-10:45'])
  })

  it('falls back to the solver catalog when the backend is unavailable', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('offline'))
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    const slots = await timeSlotService.getTimeSlots()

    expect(slots.map((s) => `${s.start_time}-${s.end_time}`)).toEqual([
      '08:00-09:15',
      '09:30-10:45',
      '11:00-12:15',
      '12:30-13:45',
      '14:00-15:15',
      '15:30-16:45',
    ])
  })
})
