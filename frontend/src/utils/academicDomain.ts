import { Room } from '../types/api'

export const CURRENT_SEMESTER_ID = 5
export const CURRENT_SEMESTER_NAME = 'Fall 2026'

export interface AcademicSemesterOption {
  id: number
  name: string
  isActive: boolean
}

export const ACADEMIC_SEMESTERS: readonly AcademicSemesterOption[] = [
  { id: 1, name: 'Fall 2024', isActive: false },
  { id: 2, name: 'Spring 2025', isActive: false },
  { id: 3, name: 'Fall 2025', isActive: false },
  { id: 4, name: 'Spring 2026', isActive: false },
  { id: 5, name: 'Fall 2026', isActive: true },
  { id: 6, name: 'Spring 2027', isActive: false },
]

export const STANDARD_DEPARTMENTS = [
  'CS',
  'ECE',
  'MATH',
  'STAT',
  'PHYS',
  'CHEM',
  'BIOL',
  'BIOE',
] as const

export type CourseLevel = 'undergraduate' | 'graduate'

export const getCourseLevel = (courseCode: string): CourseLevel => {
  const match = String(courseCode ?? '').match(/\d+/)
  if (!match) return 'undergraduate'
  const num = Number(match[0])
  if (num >= 5000 || (num >= 500 && num < 1000)) {
    return 'graduate'
  }
  return 'undergraduate'
}

export const formatCourseLevel = (level: CourseLevel): string =>
  level === 'graduate' ? 'Graduate' : 'Undergraduate'

export const BUILDING_NAME_BY_CODE: Record<string, string> = {
  FH: 'Flarsheim Hall',
  RH: 'Royall Hall',
  HH: 'Haag Hall',
  SCB: 'Spencer Chemistry Building',
  BHH: 'Bloch Heritage Hall',
  MN: 'Manheim Hall',
  BSB: 'Biological Sciences Building',
  SC: 'Siebel Center for Computer Science',
  ECEB: 'Electrical & Computer Engineering Building',
  CIF: 'Campus Instructional Facility',
  LL: 'Loomis Laboratory',
  NL: 'Noyes Laboratory',
  DCL: 'Digital Computer Laboratory',
  MSEB: 'Materials Science & Engineering Building',
}

export const resolveBuildingName = (
  room: Pick<Room, 'room_number' | 'building_name' | 'building_code'>
): string => {
  const directName = room.building_name?.trim()
  if (directName) {
    return directName
  }

  const explicitCode = room.building_code?.trim().toUpperCase()
  if (explicitCode && BUILDING_NAME_BY_CODE[explicitCode]) {
    return BUILDING_NAME_BY_CODE[explicitCode]
  }

  const prefixMatch = room.room_number?.trim().match(/^[A-Za-z]+/)
  if (prefixMatch) {
    const inferredCode = prefixMatch[0].toUpperCase()
    if (BUILDING_NAME_BY_CODE[inferredCode]) {
      return BUILDING_NAME_BY_CODE[inferredCode]
    }
  }

  return ''
}

export const formatRoomWithBuilding = (
  room: Pick<Room, 'room_number' | 'building_name' | 'building_code'>
): string => {
  const buildingName = resolveBuildingName(room)
  return buildingName ? `${room.room_number} — ${buildingName}` : room.room_number
}
