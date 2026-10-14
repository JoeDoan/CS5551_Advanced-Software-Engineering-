import { apiClient } from './apiClient'
import { TimeSlot } from '../types/api'

// Mirrors backend/data/umkc/time_slots.json, the catalog the solver reads.
const MOCK_TIME_SLOTS: TimeSlot[] = [
  { id: 1, day_pattern: 'MW', start_time: '08:00', end_time: '09:15' },
  { id: 2, day_pattern: 'MW', start_time: '09:30', end_time: '10:45' },
  { id: 3, day_pattern: 'MW', start_time: '11:00', end_time: '12:15' },
  { id: 4, day_pattern: 'MW', start_time: '12:30', end_time: '13:45' },
  { id: 5, day_pattern: 'MW', start_time: '14:00', end_time: '15:15' },
  { id: 6, day_pattern: 'MW', start_time: '15:30', end_time: '16:45' },
]

export const toSlotKey = (slot: Pick<TimeSlot, 'start_time' | 'end_time'>): string =>
  `${slot.start_time}-${slot.end_time}`

const uniqueByTimeRange = (slots: TimeSlot[]): TimeSlot[] => {
  const byKey = new Map<string, TimeSlot>()
  for (const slot of slots) {
    if (!byKey.has(toSlotKey(slot))) byKey.set(toSlotKey(slot), slot)
  }
  return [...byKey.values()].sort((a, b) => a.start_time.localeCompare(b.start_time))
}

export const timeSlotService = {
  async getTimeSlots(): Promise<TimeSlot[]> {
    try {
      const response = await apiClient.get<TimeSlot[]>('/time-slots')
      if (response.data && response.data.length > 0) {
        return uniqueByTimeRange(response.data)
      }
      return MOCK_TIME_SLOTS
    } catch {
      console.warn('Backend unavailable, using fallback time slot catalog.')
      return MOCK_TIME_SLOTS
    }
  },
}

export default timeSlotService
