import { describe, it, expect } from 'vitest'
import { preferenceService } from '../preferenceService'
import { InstructorPreference } from '../../types/api'

describe('preferenceService', () => {
  it('retrieves preferences in fallback mode', async () => {
    const prefs = await preferenceService.getPreferences()
    expect(prefs).toBeDefined()
    expect(prefs.length).toBeGreaterThan(0)
    expect(prefs[0]).toHaveProperty('user_id')
    expect(prefs[0]).toHaveProperty('preferred_days')
    expect(prefs[0]).toHaveProperty('preferred_slots')
  })

  it('filters preferences by user_id', async () => {
    const prefs = await preferenceService.getPreferences({ user_id: 1 })
    expect(prefs.length).toBeGreaterThan(0)
    for (const p of prefs) {
      expect(p.user_id).toBe(1)
    }
  })

  it('submits a new instructor preference successfully', async () => {
    const newPref: InstructorPreference = {
      user_id: 3,
      semester_id: 2,
      course_id: 5,
      preferred_days: ['Monday', 'Wednesday'],
      preferred_slots: ['14:00-15:15'],
      preferred_rooms: ['FH 256'],
      preferred_layout: 'lecture',
    }

    const result = await preferenceService.submitPreference(newPref)
    expect(result).toBeDefined()
    expect(result.id).toBeDefined()
    expect(result.user_id).toBe(3)
    expect(result.course_id).toBe(5)
  })
})
