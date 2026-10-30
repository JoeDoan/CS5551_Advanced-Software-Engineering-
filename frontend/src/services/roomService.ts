import { apiClient } from './apiClient'
import { Room, RoomFilterParams } from '../types/api'

const MOCK_ROOMS: Room[] = [
  { id: 1, room_number: 'RH 204', capacity: 48, room_type: 'lecture', building_id: 1, building_code: 'RH', building_name: 'Royall Hall' },
  { id: 2, room_number: 'RH 211', capacity: 60, room_type: 'lecture', building_id: 1, building_code: 'RH', building_name: 'Royall Hall' },
  { id: 3, room_number: 'FH 256', capacity: 75, room_type: 'auditorium', building_id: 2, building_code: 'FH', building_name: 'Flarsheim Hall' },
  { id: 4, room_number: 'FH 310', capacity: 35, room_type: 'seminar', building_id: 2, building_code: 'FH', building_name: 'Flarsheim Hall' },
  { id: 5, room_number: 'FH 464', capacity: 30, room_type: 'lab', building_id: 2, building_code: 'FH', building_name: 'Flarsheim Hall' },
  { id: 6, room_number: 'HH 201', capacity: 45, room_type: 'lecture', building_id: 3, building_code: 'HH', building_name: 'Haag Hall' },
  { id: 7, room_number: 'HH 301', capacity: 80, room_type: 'auditorium', building_id: 3, building_code: 'HH', building_name: 'Haag Hall' },
  { id: 8, room_number: 'SCB 101', capacity: 120, room_type: 'auditorium', building_id: 4, building_code: 'SCB', building_name: 'Spencer Chemistry Building' },
  { id: 9, room_number: 'SCB 205', capacity: 28, room_type: 'lab', building_id: 4, building_code: 'SCB', building_name: 'Spencer Chemistry Building' },
]

export const roomService = {
  /**
   * Fetches available classrooms and laboratories with optional filters.
   */
  async getRooms(filters?: RoomFilterParams): Promise<Room[]> {
    try {
      const params: Record<string, string | number> = {}
      if (filters?.min_capacity !== undefined) params.min_capacity = filters.min_capacity
      if (filters?.building_id !== undefined) params.building_id = filters.building_id
      if (filters?.room_type) params.room_type = filters.room_type

      const response = await apiClient.get<Room[]>('/rooms', { params })
      if (response.data && response.data.length > 0) {
        return response.data
      }
      return this._filterMock(filters)
    } catch {
      console.warn('Backend unavailable, using fallback mock rooms.')
      return this._filterMock(filters)
    }
  },

  /**
   * Retrieves a single classroom by ID.
   */
  async getRoomById(id: number): Promise<Room | null> {
    try {
      const response = await apiClient.get<Room>(`/rooms/${id}`)
      return response.data
    } catch {
      const found = MOCK_ROOMS.find((r) => r.id === id)
      return found || null
    }
  },

  async createRoom(payload: Omit<Room, 'id'>): Promise<Room> {
    try {
      const response = await apiClient.post<Room>('/rooms', payload)
      return response.data
    } catch {
      const nextId = MOCK_ROOMS.length > 0 ? Math.max(...MOCK_ROOMS.map((r) => r.id)) + 1 : 1
      const created: Room = { id: nextId, ...payload }
      MOCK_ROOMS.push(created)
      return created
    }
  },

  async updateRoom(id: number, payload: Partial<Omit<Room, 'id'>>): Promise<Room> {
    try {
      const response = await apiClient.put<Room>(`/rooms/${id}`, payload)
      return response.data
    } catch {
      const idx = MOCK_ROOMS.findIndex((r) => r.id === id)
      if (idx === -1) {
        throw new Error(`Room ${id} not found`)
      }
      MOCK_ROOMS[idx] = { ...MOCK_ROOMS[idx], ...payload }
      return MOCK_ROOMS[idx]
    }
  },

  async deleteRoom(id: number): Promise<boolean> {
    try {
      await apiClient.delete(`/rooms/${id}`)
      return true
    } catch {
      const idx = MOCK_ROOMS.findIndex((r) => r.id === id)
      if (idx !== -1) {
        MOCK_ROOMS.splice(idx, 1)
      }
      return true
    }
  },

  _filterMock(filters?: RoomFilterParams): Room[] {
    let result = [...MOCK_ROOMS]
    if (filters?.min_capacity !== undefined) {
      result = result.filter((r) => r.capacity >= (filters.min_capacity ?? 0))
    }
    if (filters?.building_id !== undefined) {
      result = result.filter((r) => r.building_id === filters.building_id)
    }
    if (filters?.room_type) {
      result = result.filter((r) => r.room_type.toLowerCase() === filters.room_type?.toLowerCase())
    }
    return result
  },
}

export default roomService
