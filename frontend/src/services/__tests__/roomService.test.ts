import { describe, it, expect } from 'vitest'
import { roomService } from '../roomService'

describe('roomService', () => {
  it('retrieves classrooms list in fallback mode', async () => {
    const rooms = await roomService.getRooms()
    expect(rooms).toBeDefined()
    expect(rooms.length).toBeGreaterThan(0)
    expect(rooms[0]).toHaveProperty('room_number')
    expect(rooms[0]).toHaveProperty('capacity')
    expect(rooms[0]).toHaveProperty('room_type')
  })

  it('filters rooms by minimum capacity', async () => {
    const minCap = 60
    const largeRooms = await roomService.getRooms({ min_capacity: minCap })
    expect(largeRooms.length).toBeGreaterThan(0)
    for (const r of largeRooms) {
      expect(r.capacity).toBeGreaterThanOrEqual(minCap)
    }
  })

  it('filters rooms by room type (lab)', async () => {
    const labs = await roomService.getRooms({ room_type: 'lab' })
    expect(labs.length).toBeGreaterThan(0)
    for (const r of labs) {
      expect(r.room_type).toBe('lab')
    }
  })

  it('retrieves room by valid ID', async () => {
    const room = await roomService.getRoomById(1)
    expect(room).toBeDefined()
    expect(room?.id).toBe(1)
    expect(room?.room_number).toBe('RH 204')
  })

  it('returns null for an invalid room ID', async () => {
    const room = await roomService.getRoomById(9999)
    expect(room).toBeNull()
  })
})
