import { ScheduleEvent } from '../types/api'

export interface ClientConflictItem {
  id: string
  type: 'ROOM_DOUBLE_BOOKING' | 'INSTRUCTOR_DOUBLE_BOOKING' | 'INSTRUCTOR_OVERLOAD'
  severity: 'hard' | 'soft'
  description: string
  courseCodes: string[]
  roomNumber?: string
  instructorName?: string
  timeSlotLabel?: string
}

export interface CourseDiffEntry {
  course_code: string
  course_name: string
  oldRoom?: string
  newRoom?: string
  oldSlot?: string
  newSlot?: string
  oldInstructor?: string
  newInstructor?: string
}

export interface SemesterDiffReport {
  addedCourses: CourseDiffEntry[]
  removedCourses: CourseDiffEntry[]
  roomChangedCourses: CourseDiffEntry[]
  slotChangedCourses: CourseDiffEntry[]
  unchangedCount: number
}

export function detectScheduleConflicts(events: ScheduleEvent[]): ClientConflictItem[] {
  const conflicts: ClientConflictItem[] = []
  const roomSlotMap = new Map<string, ScheduleEvent[]>()
  const instSlotMap = new Map<string, ScheduleEvent[]>()
  const instLoadMap = new Map<string, ScheduleEvent[]>()

  for (const ev of events) {
    const slotKey = `${ev.day_pattern}|${ev.start_time}-${ev.end_time}`
    const rKey = `${ev.room_number}::${slotKey}`
    const iKey = `${ev.instructor_name}::${slotKey}`

    roomSlotMap.set(rKey, [...(roomSlotMap.get(rKey) || []), ev])
    instSlotMap.set(iKey, [...(instSlotMap.get(iKey) || []), ev])
    instLoadMap.set(
      ev.instructor_name,
      [...(instLoadMap.get(ev.instructor_name) || []), ev]
    )
  }

  for (const [key, group] of roomSlotMap.entries()) {
    if (group.length > 1) {
      const [roomNumber, slotLabel] = key.split('::')
      const codes = group.map((g) => g.course_code)
      conflicts.push({
        id: `room-${key}`,
        type: 'ROOM_DOUBLE_BOOKING',
        severity: 'hard',
        roomNumber,
        timeSlotLabel: slotLabel,
        courseCodes: codes,
        description: `Room ${roomNumber} is double-booked by ${codes.join(', ')} during ${slotLabel.replace('|', ' ')}`,
      })
    }
  }

  for (const [key, group] of instSlotMap.entries()) {
    if (group.length > 1) {
      const [instructorName, slotLabel] = key.split('::')
      const codes = group.map((g) => g.course_code)
      conflicts.push({
        id: `inst-${key}`,
        type: 'INSTRUCTOR_DOUBLE_BOOKING',
        severity: 'hard',
        instructorName,
        timeSlotLabel: slotLabel,
        courseCodes: codes,
        description: `Instructor ${instructorName} is assigned to ${codes.join(', ')} simultaneously during ${slotLabel.replace('|', ' ')}`,
      })
    }
  }

  for (const [instructorName, group] of instLoadMap.entries()) {
    if (group.length > 2) {
      const codes = group.map((g) => g.course_code)
      conflicts.push({
        id: `overload-${instructorName}`,
        type: 'INSTRUCTOR_OVERLOAD',
        severity: 'soft',
        instructorName,
        courseCodes: codes,
        description: `Instructor ${instructorName} has ${group.length} assigned courses (${codes.join(', ')}), exceeding the standard 2-course cap`,
      })
    }
  }

  return conflicts
}

export function compareSemesters(
  baseEvents: ScheduleEvent[],
  targetEvents: ScheduleEvent[]
): SemesterDiffReport {
  const baseByCode = new Map<string, ScheduleEvent>()
  const targetByCode = new Map<string, ScheduleEvent>()

  for (const ev of baseEvents) {
    baseByCode.set(ev.course_code, ev)
  }
  for (const ev of targetEvents) {
    targetByCode.set(ev.course_code, ev)
  }

  const addedCourses: CourseDiffEntry[] = []
  const removedCourses: CourseDiffEntry[] = []
  const roomChangedCourses: CourseDiffEntry[] = []
  const slotChangedCourses: CourseDiffEntry[] = []
  let unchangedCount = 0

  for (const [code, tgt] of targetByCode.entries()) {
    const base = baseByCode.get(code)
    if (!base) {
      addedCourses.push({
        course_code: code,
        course_name: tgt.course_name,
        newRoom: tgt.room_number,
        newSlot: `${tgt.day_pattern} ${tgt.start_time}-${tgt.end_time}`,
        newInstructor: tgt.instructor_name,
      })
      continue
    }

    const baseSlot = `${base.day_pattern} ${base.start_time}-${base.end_time}`
    const tgtSlot = `${tgt.day_pattern} ${tgt.start_time}-${tgt.end_time}`
    const roomDiff = base.room_number !== tgt.room_number
    const slotDiff = baseSlot !== tgtSlot

    if (roomDiff) {
      roomChangedCourses.push({
        course_code: code,
        course_name: tgt.course_name,
        oldRoom: base.room_number,
        newRoom: tgt.room_number,
        oldSlot: baseSlot,
        newSlot: tgtSlot,
      })
    }
    if (slotDiff) {
      slotChangedCourses.push({
        course_code: code,
        course_name: tgt.course_name,
        oldSlot: baseSlot,
        newSlot: tgtSlot,
        oldRoom: base.room_number,
        newRoom: tgt.room_number,
      })
    }
    if (!roomDiff && !slotDiff) {
      unchangedCount += 1
    }
  }

  for (const [code, base] of baseByCode.entries()) {
    if (!targetByCode.has(code)) {
      removedCourses.push({
        course_code: code,
        course_name: base.course_name,
        oldRoom: base.room_number,
        oldSlot: `${base.day_pattern} ${base.start_time}-${base.end_time}`,
        oldInstructor: base.instructor_name,
      })
    }
  }

  return {
    addedCourses,
    removedCourses,
    roomChangedCourses,
    slotChangedCourses,
    unchangedCount,
  }
}
