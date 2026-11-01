import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Clock,
  Check,
  Trash2,
  Edit3,
  Building2,
  BookOpen,
  UserCheck,
  CalendarDays,
  GraduationCap,
  Eye,
} from 'lucide-react'
import {
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Select,
} from '../components/ui'
import { Toast } from '../components/common/Toast'
import { preferenceService } from '../services/preferenceService'
import { DEFAULT_INSTRUCTORS, instructorService } from '../services/instructorService'
import { timeSlotService, toSlotKey } from '../services/timeSlotService'
import { roomService } from '../services/roomService'
import { courseAssignmentService } from '../services/courseAssignmentService'
import { scheduleService } from '../services/scheduleService'
import {
  InstructorPreference,
  InstructorSummary,
  Room,
  TimeSlot,
} from '../types/api'
import { useAuth } from '../context/AuthContext'
import {
  CURRENT_SEMESTER_ID,
  CURRENT_SEMESTER_NAME,
  CourseLevel,
  formatCourseLevel,
  getCourseLevel,
  resolveBuildingName,
} from '../utils/academicDomain'

const DAY_CATALOG = [
  { code: 'M', aliases: ['monday', 'mon'], label: 'Monday (M)' },
  { code: 'T', aliases: ['tuesday', 'tue', 'tues'], label: 'Tuesday (T)' },
  { code: 'W', aliases: ['wednesday', 'wed'], label: 'Wednesday (W)' },
  { code: 'R', aliases: ['thursday', 'thu', 'thur', 'thurs'], label: 'Thursday (R)' },
  { code: 'F', aliases: ['friday', 'fri'], label: 'Friday (F)' },
] as const

const DAY_OPTIONS = DAY_CATALOG.map((d) => d.label)

interface AssignedCourseDisplay {
  course_id: number
  course_code: string
  course_name: string
  course_level: CourseLevel
}

export const normalizeStoredDaysToLabels = (
  rawDays: string[] | string | undefined | null
): string[] => {
  if (!rawDays) return []
  const tokens = Array.isArray(rawDays) ? rawDays : rawDays.split(/[\s,;/]+/)
  const matchedCodes = new Set<string>()

  for (const raw of tokens) {
    const trimmed = String(raw ?? '').trim()
    if (!trimmed) continue

    const parenMatch = trimmed.match(/\(([MTWRF])\)/i)
    if (parenMatch) {
      matchedCodes.add(parenMatch[1].toUpperCase())
      continue
    }

    const lower = trimmed.toLowerCase()
    const byAlias = DAY_CATALOG.find((d) =>
      (d.aliases as readonly string[]).includes(lower)
    )
    if (byAlias) {
      matchedCodes.add(byAlias.code)
      continue
    }

    if (/^[MTWRF]+$/i.test(trimmed)) {
      for (const ch of trimmed.toUpperCase()) {
        matchedCodes.add(ch)
      }
    }
  }

  return DAY_CATALOG.filter((d) => matchedCodes.has(d.code)).map((d) => d.label)
}

const toInstructorOptions = (list: InstructorSummary[]) =>
  list.map((inst) => ({
    value: String(inst.id),
    label: `${inst.full_name} (${inst.department})`,
  }))

export const PreferencesPage: React.FC = () => {
  const { user, isStandaloneFallback } = useAuth()
  const isLockedInstructor =
    !isStandaloneFallback && user?.role === 'instructor' && user.linked_user_id !== null
  const isReadOnlyCoordinator = !isStandaloneFallback && user?.role === 'coordinator'

  const [instructorList, setInstructorList] = useState<InstructorSummary[]>(DEFAULT_INSTRUCTORS)
  const [selectedInstructor, setSelectedInstructor] = useState<string>(() =>
    isLockedInstructor && user?.linked_user_id ? String(user.linked_user_id) : '1'
  )

  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [savedPreferences, setSavedPreferences] = useState<InstructorPreference[]>([])
  const [assignedCourses, setAssignedCourses] = useState<AssignedCourseDisplay[]>([])

  const [selectedDays, setSelectedDays] = useState<string[]>(() =>
    isReadOnlyCoordinator ? [] : ['Monday (M)', 'Wednesday (W)']
  )
  const [selectedSlots, setSelectedSlots] = useState<string[]>([])
  const [selectedRooms, setSelectedRooms] = useState<string[]>([])
  const [toast, setToast] = useState<{
    type: 'success' | 'error' | 'warning'
    message: string
  } | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const hasUserEditedRef = useRef<boolean>(false)

  useEffect(() => {
    let active = true
    timeSlotService.getTimeSlots().then((slots) => {
      if (active) setTimeSlots(slots)
    })
    roomService.getRooms().then((catalogRooms) => {
      if (active) setRooms(catalogRooms)
    })
    if (isStandaloneFallback || !isLockedInstructor) {
      instructorService.getInstructors().then((loaded) => {
        if (active) setInstructorList(loaded)
      })
    }
    return () => {
      active = false
    }
  }, [isStandaloneFallback, isLockedInstructor])

  useEffect(() => {
    if (isLockedInstructor && user?.linked_user_id) {
      hasUserEditedRef.current = false
      setSelectedInstructor(String(user.linked_user_id))
    }
  }, [isLockedInstructor, user?.linked_user_id])

  const activeInstructorName = useMemo(() => {
    if (isLockedInstructor && user?.full_name) return user.full_name
    return instructorList.find((inst) => String(inst.id) === selectedInstructor)?.full_name ?? ''
  }, [isLockedInstructor, user, instructorList, selectedInstructor])

  useEffect(() => {
    let active = true
    const userId = Number(selectedInstructor)
    if (!userId) return

    preferenceService
      .getPreferences({
        user_id: userId,
        semester_id: CURRENT_SEMESTER_ID,
        general_only: true,
      })
      .then((list) => {
        if (!active) return
        const generalOnly = (Array.isArray(list) ? list : []).filter(
          (p) => p.course_id == null
        )
        setSavedPreferences(generalOnly)
      })
      .catch(() => {
        if (active) setSavedPreferences([])
      })

    Promise.all([
      courseAssignmentService
        .getAssignments({ semester_id: CURRENT_SEMESTER_ID, user_id: userId })
        .catch(() => []),
      scheduleService.getSchedules(CURRENT_SEMESTER_ID).catch(() => []),
    ]).then(([explicitAssignments, semesterSchedules]) => {
      if (!active) return
      const normalizedTargetName = activeInstructorName.trim().toLowerCase()
      const byCode = new Map<string, AssignedCourseDisplay>()

      for (const item of explicitAssignments) {
        if (item.user_id !== userId) continue
        const key = item.course_code.trim().toUpperCase()
        if (!key) continue
        byCode.set(key, {
          course_id: item.course_id,
          course_code: item.course_code,
          course_name: item.course_name,
          course_level: item.course_level ?? getCourseLevel(item.course_code),
        })
      }

      for (const ev of semesterSchedules) {
        const matchesId = ev.user_id === userId || ev.instructor_id === userId
        const matchesName =
          Boolean(normalizedTargetName) &&
          (ev.instructor_name || '').trim().toLowerCase() === normalizedTargetName
        if (!matchesId && !matchesName) continue
        const key = (ev.course_code || '').trim().toUpperCase()
        if (!key || byCode.has(key)) continue
        byCode.set(key, {
          course_id: ev.course_id,
          course_code: ev.course_code,
          course_name: ev.course_name,
          course_level: getCourseLevel(ev.course_code),
        })
      }

      const merged = Array.from(byCode.values()).sort((a, b) =>
        a.course_code.localeCompare(b.course_code)
      )
      setAssignedCourses(merged)
    })

    return () => {
      active = false
    }
  }, [selectedInstructor, activeInstructorName])

  useEffect(() => {
    const match = savedPreferences.find((p) => p.course_id == null)

    if (match) {
      if (!hasUserEditedRef.current) {
        setSelectedDays(normalizeStoredDaysToLabels(match.preferred_days))
        setSelectedSlots(Array.isArray(match.preferred_slots) ? [...match.preferred_slots] : [])
        setSelectedRooms(Array.isArray(match.preferred_rooms) ? [...match.preferred_rooms] : [])
      }
    } else if (!hasUserEditedRef.current) {
      setSelectedDays(isReadOnlyCoordinator ? [] : ['Monday (M)', 'Wednesday (W)'])
      setSelectedSlots([])
      setSelectedRooms([])
    }
  }, [savedPreferences, isReadOnlyCoordinator])

  const instructors = useMemo(() => {
    const base = toInstructorOptions(instructorList)
    if (
      isLockedInstructor &&
      user?.linked_user_id &&
      !base.some((opt) => opt.value === String(user.linked_user_id))
    ) {
      base.unshift({
        value: String(user.linked_user_id),
        label: `${user.full_name} (${user.department})`,
      })
    }
    return base
  }, [instructorList, isLockedInstructor, user])

  const toggleDay = (day: string) => {
    if (isReadOnlyCoordinator) return
    hasUserEditedRef.current = true
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const applyDayPreset = (days: string[]) => {
    if (isReadOnlyCoordinator) return
    hasUserEditedRef.current = true
    setSelectedDays(days)
  }

  const toggleSlot = (slot: string) => {
    if (isReadOnlyCoordinator) return
    hasUserEditedRef.current = true
    setSelectedSlots((prev) =>
      prev.includes(slot) ? prev.filter((s) => s !== slot) : [...prev, slot]
    )
  }

  const toggleRoom = (roomNumber: string) => {
    if (isReadOnlyCoordinator) return
    hasUserEditedRef.current = true
    setSelectedRooms((prev) =>
      prev.includes(roomNumber)
        ? prev.filter((r) => r !== roomNumber)
        : [...prev, roomNumber]
    )
  }

  const handleLoadSaved = (pref: InstructorPreference) => {
    if (isReadOnlyCoordinator) return
    hasUserEditedRef.current = false
    setSelectedDays(normalizeStoredDaysToLabels(pref.preferred_days))
    setSelectedSlots(Array.isArray(pref.preferred_slots) ? [...pref.preferred_slots] : [])
    setSelectedRooms(Array.isArray(pref.preferred_rooms) ? [...pref.preferred_rooms] : [])
    setToast(null)
  }

  const handleDeleteSaved = async (pref: InstructorPreference) => {
    if (isReadOnlyCoordinator) return
    if (pref.id == null) return
    try {
      await preferenceService.deletePreference(pref.id)
      hasUserEditedRef.current = false
      setSavedPreferences((prev) => prev.filter((item) => item.id !== pref.id))
      setToast({
        type: 'success',
        message: 'Saved preference deleted.',
      })
    } catch (err) {
      setToast({
        type: 'error',
        message:
          err instanceof Error && err.message
            ? err.message
            : 'Failed to delete saved preference.',
      })
    }
  }

  const handleSavePreferences = async () => {
    if (isReadOnlyCoordinator) return
    if (selectedDays.length === 0 || selectedSlots.length === 0) {
      setToast({
        type: 'error',
        message: 'Please select at least one teaching day and one time slot.',
      })
      return
    }

    try {
      setIsSubmitting(true)
      const mappedDays = DAY_CATALOG.filter((d) => selectedDays.includes(d.label)).map(
        (d) => d.code
      )

      const saved = await preferenceService.submitPreference({
        user_id: Number(selectedInstructor),
        semester_id: CURRENT_SEMESTER_ID,
        course_id: null,
        preferred_days: mappedDays,
        preferred_slots: selectedSlots,
        preferred_rooms: selectedRooms,
      })

      hasUserEditedRef.current = false
      setSavedPreferences((prev) => {
        const normalizedSaved: InstructorPreference = {
          ...saved,
          semester_id: CURRENT_SEMESTER_ID,
          course_id: null,
          preferred_days: saved.preferred_days ?? mappedDays,
          preferred_slots: saved.preferred_slots ?? selectedSlots,
          preferred_rooms: saved.preferred_rooms ?? selectedRooms,
        }
        const idx = prev.findIndex((item) => item.course_id == null)
        if (idx !== -1) {
          const next = [...prev]
          next[idx] = { ...prev[idx], ...normalizedSaved }
          return next
        }
        return [...prev, normalizedSaved]
      })

      setToast({
        type: 'success',
        message: 'Instructor preferences saved successfully!',
      })
    } catch (err) {
      const errMsg =
        err instanceof Error &&
        err.message &&
        err.message !== 'API failure' &&
        !err.message.startsWith('Network error')
          ? err.message
          : 'Failed to save preferences. Please check backend connection.'
      setToast({
        type: 'error',
        message: errMsg,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    if (isReadOnlyCoordinator) return
    hasUserEditedRef.current = true
    setSelectedDays([])
    setSelectedSlots([])
    setSelectedRooms([])
    setToast(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Instructor Preferences</h1>
          <p className="text-sm text-slate-500 mt-1">
            {isReadOnlyCoordinator
              ? `Inspect ${CURRENT_SEMESTER_NAME} faculty teaching availability and preferred classrooms for the CP-SAT schedule optimizer.`
              : `Configure your ${CURRENT_SEMESTER_NAME} teaching availability and preferred classrooms for the CP-SAT schedule optimizer.`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {isReadOnlyCoordinator && <Badge variant="neutral">Read-Only View</Badge>}

          <div
            data-testid="active-semester-badge"
            className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800"
          >
            <CalendarDays className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Current Term: {CURRENT_SEMESTER_NAME}</span>
          </div>

          {isLockedInstructor && user && (
            <div className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-800">
              <UserCheck className="w-4 h-4 text-blue-600 shrink-0" />
              <span className="font-semibold">{user.full_name}</span>
              <Badge variant="info">{user.department}</Badge>
            </div>
          )}
        </div>
      </div>

      {isReadOnlyCoordinator && (
        <div
          data-testid="coordinator-readonly-banner"
          className="flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-700"
        >
          <Eye className="w-4 h-4 text-slate-600 shrink-0" />
          <span>
            <span className="font-semibold text-slate-900">View-Only Mode:</span> Course
            Coordinators can inspect faculty availability profiles. Only instructors can modify
            their own teaching preferences.
          </span>
        </div>
      )}

      <Card data-testid="coordinator-assigned-courses">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 py-3.5">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
              <GraduationCap className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-sm">
                Coordinator-Assigned Courses ({CURRENT_SEMESTER_NAME})
              </CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                {isReadOnlyCoordinator
                  ? 'Teaching load assigned to the selected instructor'
                  : 'Read-only teaching load assigned by your Course Coordinator'}
              </p>
            </div>
          </div>
          <Badge variant="neutral">
            {assignedCourses.length} Assigned {assignedCourses.length === 1 ? 'Course' : 'Courses'}
          </Badge>
        </CardHeader>
        <CardContent className="pt-0 pb-4">
          {assignedCourses.length === 0 ? (
            <p className="text-xs text-slate-500">
              Course teaching assignments for {CURRENT_SEMESTER_NAME} are managed by your Course
              Coordinator.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {assignedCourses.map((course) => (
                <div
                  key={`${course.course_id}-${course.course_code}`}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-xs"
                >
                  <span className="font-bold text-slate-900">{course.course_code}</span>
                  <span className="text-slate-600">{course.course_name}</span>
                  <Badge variant={course.course_level === 'graduate' ? 'gold' : 'info'}>
                    {formatCourseLevel(course.course_level)}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle>Teaching Availability & Classroom Preferences</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              {isReadOnlyCoordinator
                ? `General availability across all courses assigned to this instructor in ${CURRENT_SEMESTER_NAME}.`
                : `General availability applies across all courses assigned to you in ${CURRENT_SEMESTER_NAME}.`}
            </p>
          </div>
          <Badge variant="info">General Availability</Badge>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select
              label="Select Instructor"
              options={instructors}
              value={selectedInstructor}
              disabled={isLockedInstructor}
              helperText={
                isLockedInstructor
                  ? 'Locked to your authenticated faculty profile.'
                  : isReadOnlyCoordinator
                    ? 'Switch faculty profiles to inspect their saved availability.'
                    : undefined
              }
              onChange={(e) => {
                hasUserEditedRef.current = false
                setSelectedInstructor(e.target.value)
              }}
              data-testid="instructor-select"
            />
          </div>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <label className="block text-xs font-semibold text-slate-700">
                Preferred Days {!isReadOnlyCoordinator && <span className="text-red-500">*</span>}
              </label>
              {!isReadOnlyCoordinator && (
                <div className="flex items-center space-x-1.5 text-xs">
                  <span className="text-slate-400 font-medium">Quick patterns:</span>
                  <button
                    type="button"
                    onClick={() =>
                      applyDayPreset(['Monday (M)', 'Wednesday (W)', 'Friday (F)'])
                    }
                    data-testid="preset-days-mwf"
                    className="px-2 py-0.5 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 font-medium transition-colors"
                  >
                    MWF
                  </button>
                  <button
                    type="button"
                    onClick={() => applyDayPreset(['Tuesday (T)', 'Thursday (R)'])}
                    data-testid="preset-days-tr"
                    className="px-2 py-0.5 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 font-medium transition-colors"
                  >
                    TR
                  </button>
                  <button
                    type="button"
                    onClick={() => applyDayPreset([...DAY_OPTIONS])}
                    data-testid="preset-days-all"
                    className="px-2 py-0.5 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 font-medium transition-colors"
                  >
                    All Weekdays
                  </button>
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {DAY_OPTIONS.map((day) => {
                const isSelected = selectedDays.includes(day)
                return (
                  <Button
                    key={day}
                    type="button"
                    variant={isSelected ? 'primary' : 'outline'}
                    size="sm"
                    disabled={isReadOnlyCoordinator}
                    className={
                      isReadOnlyCoordinator
                        ? isSelected
                          ? 'disabled:!opacity-100 disabled:!cursor-default hover:bg-umkc-blue-700'
                          : 'disabled:!opacity-100 disabled:!cursor-default hover:bg-white'
                        : undefined
                    }
                    onClick={() => toggleDay(day)}
                    aria-pressed={isSelected}
                    data-testid={`day-btn-${day}`}
                  >
                    {day}
                  </Button>
                )
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Preferred Time Slots{' '}
              {!isReadOnlyCoordinator && <span className="text-red-500">*</span>}
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              {timeSlots.map((timeSlot) => {
                const slot = toSlotKey(timeSlot)
                const isSelected = selectedSlots.includes(slot)
                return (
                  <button
                    key={slot}
                    type="button"
                    disabled={isReadOnlyCoordinator}
                    data-testid={`slot-${slot}`}
                    aria-pressed={isSelected}
                    onClick={() => toggleSlot(slot)}
                    className={`p-2.5 rounded-xl border text-xs flex items-center justify-between gap-1.5 transition-all ${
                      isReadOnlyCoordinator ? 'cursor-default' : 'cursor-pointer'
                    } text-left focus:outline-none ${
                      isSelected
                        ? 'bg-blue-50 border-blue-600 text-blue-700 font-semibold ring-2 ring-blue-500/20'
                        : isReadOnlyCoordinator
                          ? 'border-slate-200 text-slate-600 bg-slate-50'
                          : 'border-slate-200 text-slate-600 bg-slate-50 hover:bg-slate-100/80 hover:border-slate-300'
                    }`}
                  >
                    <span className="flex items-center space-x-2 min-w-0">
                      <Clock
                        className={`w-3.5 h-3.5 flex-shrink-0 ${
                          isSelected ? 'text-blue-600' : 'text-slate-400'
                        }`}
                      />
                      <span className="truncate">{`${timeSlot.start_time} - ${timeSlot.end_time}`}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          <div data-testid="preferred-rooms-section">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-slate-700">
                Preferred Classrooms & Labs{' '}
                <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              {selectedRooms.length > 0 && (
                <span className="text-xs font-medium text-blue-700">
                  {selectedRooms.length} selected
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {rooms.map((room) => {
                const isSelected = selectedRooms.includes(room.room_number)
                const isLab = room.room_type.toLowerCase().includes('lab')
                const buildingName = resolveBuildingName(room)
                return (
                  <button
                    key={room.id}
                    type="button"
                    disabled={isReadOnlyCoordinator}
                    data-testid={`room-chip-${room.room_number}`}
                    aria-pressed={isSelected}
                    onClick={() => toggleRoom(room.room_number)}
                    className={`px-3 py-2.5 rounded-xl border text-xs flex items-center justify-between gap-2 transition-all ${
                      isReadOnlyCoordinator ? 'cursor-default' : 'cursor-pointer'
                    } text-left focus:outline-none ${
                      isSelected
                        ? 'bg-blue-50 border-blue-600 text-blue-800 font-semibold ring-2 ring-blue-500/20'
                        : isReadOnlyCoordinator
                          ? 'border-slate-200 text-slate-700 bg-slate-50'
                          : 'border-slate-200 text-slate-700 bg-slate-50 hover:bg-slate-100/80 hover:border-slate-300'
                    }`}
                  >
                    <span className="flex items-center space-x-2 min-w-0">
                      <Building2
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isSelected ? 'text-blue-600' : 'text-slate-400'
                        }`}
                      />
                      <span className="font-semibold shrink-0">{room.room_number}</span>
                      {buildingName && (
                        <span className="text-slate-600 font-normal truncate">
                          · {buildingName}
                        </span>
                      )}
                      <span className="text-slate-500 font-normal shrink-0">
                        · Cap {room.capacity}
                      </span>
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                        isLab
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-200/80 text-slate-700'
                      }`}
                    >
                      {isLab ? 'LAB' : 'LECTURE'}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {!isReadOnlyCoordinator && (
            <div className="pt-2 flex items-center space-x-3">
              <Button
                variant="primary"
                onClick={handleSavePreferences}
                isLoading={isSubmitting}
                leftIcon={<Check className="w-4 h-4" />}
                data-testid="save-preferences-button"
              >
                Save Preferences
              </Button>
              <Button
                variant="secondary"
                type="button"
                onClick={handleReset}
                disabled={isSubmitting}
                data-testid="reset-preferences-button"
              >
                Reset
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card data-testid="saved-preferences-list">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <CardTitle>Saved Availability Profile ({CURRENT_SEMESTER_NAME})</CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                {CURRENT_SEMESTER_NAME} ({savedPreferences.length} saved profile
                {savedPreferences.length === 1 ? '' : 's'})
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {savedPreferences.length === 0 ? (
            <p className="text-xs text-slate-500 py-3">
              {isReadOnlyCoordinator
                ? `No saved preferences recorded for this instructor in ${CURRENT_SEMESTER_NAME} yet.`
                : `No saved preferences recorded for ${CURRENT_SEMESTER_NAME} yet. Select days and time slots above to save your availability.`}
            </p>
          ) : (
            <div className="space-y-3">
              {savedPreferences.map((pref) => {
                const dayBadges = normalizeStoredDaysToLabels(pref.preferred_days).map((label) => {
                  const m = label.match(/\(([MTWRF])\)/)
                  return m ? m[1] : label
                })

                return (
                  <div
                    key={pref.id ?? `${pref.user_id}-${pref.semester_id}-gen`}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 rounded-xl border border-blue-300 bg-blue-50/40 transition-colors"
                  >
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="info">General Availability</Badge>
                        <Badge variant="success">Active Term</Badge>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
                        <span className="font-semibold text-slate-700">Days:</span>
                        {dayBadges.map((d) => (
                          <Badge key={d} variant="neutral">
                            {d}
                          </Badge>
                        ))}
                        <span className="font-semibold text-slate-700 ml-2">Slots:</span>
                        {(pref.preferred_slots ?? []).map((s) => (
                          <Badge key={s} variant="neutral">
                            {s}
                          </Badge>
                        ))}
                        {Array.isArray(pref.preferred_rooms) && pref.preferred_rooms.length > 0 && (
                          <>
                            <span className="font-semibold text-slate-700 ml-2">Classrooms:</span>
                            {pref.preferred_rooms.map((rm) => (
                              <Badge key={rm} variant="info">
                                {rm}
                              </Badge>
                            ))}
                          </>
                        )}
                      </div>
                    </div>

                    {!isReadOnlyCoordinator && (
                      <div className="flex items-center space-x-2 shrink-0">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          leftIcon={<Edit3 className="w-3.5 h-3.5" />}
                          onClick={() => handleLoadSaved(pref)}
                          data-testid={`edit-pref-${pref.id}`}
                        >
                          Load & Edit
                        </Button>
                        {pref.id != null && (
                          <Button
                            type="button"
                            variant="danger"
                            size="sm"
                            leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                            onClick={() => handleDeleteSaved(pref)}
                            data-testid={`delete-pref-${pref.id}`}
                          >
                            Delete
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}

export default PreferencesPage
