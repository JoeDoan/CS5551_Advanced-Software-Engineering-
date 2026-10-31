import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Clock, Check, Trash2, Edit3, Building2, BookOpen, UserCheck } from 'lucide-react'
import {
  Alert,
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
import { courseService } from '../services/courseService'
import { roomService } from '../services/roomService'
import {
  Course,
  InstructorPreference,
  InstructorSummary,
  Room,
  TimeSlot,
} from '../types/api'
import { useAuth } from '../context/AuthContext'

export type PreferenceScope = { kind: 'general' } | { kind: 'course'; courseId: number }

const DAY_CATALOG = [
  { code: 'M', aliases: ['monday', 'mon'], label: 'Monday (M)' },
  { code: 'T', aliases: ['tuesday', 'tue', 'tues'], label: 'Tuesday (T)' },
  { code: 'W', aliases: ['wednesday', 'wed'], label: 'Wednesday (W)' },
  { code: 'R', aliases: ['thursday', 'thu', 'thur', 'thurs'], label: 'Thursday (R)' },
  { code: 'F', aliases: ['friday', 'fri'], label: 'Friday (F)' },
] as const

const DAY_OPTIONS = DAY_CATALOG.map((d) => d.label)

const SEMESTER_OPTIONS = [
  { value: '1', label: 'Semester 1 — Fall 2024' },
  { value: '2', label: 'Semester 2 — Spring 2025' },
  { value: '3', label: 'Semester 3 — Fall 2025' },
  { value: '4', label: 'Semester 4 — Spring 2026' },
  { value: '5', label: 'Semester 5 — Fall 2026' },
  { value: '6', label: 'Semester 6 — Spring 2027' },
]

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

  const [instructorList, setInstructorList] = useState<InstructorSummary[]>(DEFAULT_INSTRUCTORS)
  const [selectedInstructor, setSelectedInstructor] = useState<string>(() =>
    isLockedInstructor && user?.linked_user_id ? String(user.linked_user_id) : '1'
  )
  const [selectedSemester, setSelectedSemester] = useState<number>(1)
  const [scope, setScope] = useState<PreferenceScope>({ kind: 'general' })

  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [savedPreferences, setSavedPreferences] = useState<InstructorPreference[]>([])

  const [selectedDays, setSelectedDays] = useState<string[]>(['Monday (M)', 'Wednesday (W)'])
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
    courseService.getCourses().then((catalogCourses) => {
      if (active) setCourses(catalogCourses)
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

  useEffect(() => {
    let active = true
    const userId = Number(selectedInstructor)
    if (!userId) return

    preferenceService
      .getPreferences({ user_id: userId, semester_id: selectedSemester })
      .then((list) => {
        if (!active) return
        setSavedPreferences(Array.isArray(list) ? list : [])
      })
      .catch(() => {
        if (active) setSavedPreferences([])
      })

    return () => {
      active = false
    }
  }, [selectedInstructor, selectedSemester])

  const activeScopeKey = scope.kind === 'general' ? 'GENERAL' : `COURSE:${scope.courseId}`

  useEffect(() => {
    const match =
      scope.kind === 'general'
        ? savedPreferences.find((p) => p.course_id == null)
        : savedPreferences.find((p) => p.course_id === scope.courseId)

    if (match) {
      if (!hasUserEditedRef.current) {
        setSelectedDays(normalizeStoredDaysToLabels(match.preferred_days))
        setSelectedSlots(Array.isArray(match.preferred_slots) ? [...match.preferred_slots] : [])
        setSelectedRooms(Array.isArray(match.preferred_rooms) ? [...match.preferred_rooms] : [])
      }
    } else if (!hasUserEditedRef.current) {
      setSelectedDays(['Monday (M)', 'Wednesday (W)'])
      setSelectedSlots([])
      setSelectedRooms([])
    }
  }, [savedPreferences, activeScopeKey, scope])

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

  const activeDepartment = useMemo(() => {
    if (isLockedInstructor && user?.department) return user.department
    const found = instructorList.find((inst) => String(inst.id) === selectedInstructor)
    return found?.department ?? ''
  }, [isLockedInstructor, user, instructorList, selectedInstructor])

  const courseOptions = useMemo(() => {
    const deptUpper = activeDepartment.toUpperCase()
    const sorted = [...courses].sort((a, b) => {
      const aMatch = deptUpper && a.department.toUpperCase() === deptUpper ? 0 : 1
      const bMatch = deptUpper && b.department.toUpperCase() === deptUpper ? 0 : 1
      if (aMatch !== bMatch) return aMatch - bMatch
      return a.course_code.localeCompare(b.course_code)
    })

    return [
      {
        value: 'GENERAL',
        label: 'General Semester Availability (All Assigned Courses)',
      },
      ...sorted.map((c) => ({
        value: String(c.id),
        label: `${c.course_code} — ${c.course_name} (Dept: ${c.department})`,
      })),
    ]
  }, [courses, activeDepartment])

  const courseById = useMemo(() => {
    const map = new Map<number, Course>()
    for (const c of courses) {
      map.set(c.id, c)
    }
    return map
  }, [courses])

  const hasSavedGeneral = savedPreferences.some((p) => p.course_id == null)
  const courseSpecificCount = savedPreferences.filter((p) => p.course_id != null).length

  const toggleDay = (day: string) => {
    hasUserEditedRef.current = true
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const applyDayPreset = (days: string[]) => {
    hasUserEditedRef.current = true
    setSelectedDays(days)
  }

  const toggleSlot = (slot: string) => {
    hasUserEditedRef.current = true
    setSelectedSlots((prev) =>
      prev.includes(slot) ? prev.filter((s) => s !== slot) : [...prev, slot]
    )
  }

  const toggleRoom = (roomNumber: string) => {
    hasUserEditedRef.current = true
    setSelectedRooms((prev) =>
      prev.includes(roomNumber)
        ? prev.filter((r) => r !== roomNumber)
        : [...prev, roomNumber]
    )
  }

  const handleLoadSaved = (pref: InstructorPreference) => {
    hasUserEditedRef.current = false
    const nextScope: PreferenceScope =
      pref.course_id == null
        ? { kind: 'general' }
        : { kind: 'course', courseId: pref.course_id }
    setScope(nextScope)
    setSelectedDays(normalizeStoredDaysToLabels(pref.preferred_days))
    setSelectedSlots(Array.isArray(pref.preferred_slots) ? [...pref.preferred_slots] : [])
    setSelectedRooms(Array.isArray(pref.preferred_rooms) ? [...pref.preferred_rooms] : [])
    setToast(null)
  }

  const handleDeleteSaved = async (pref: InstructorPreference) => {
    if (pref.id == null) return
    try {
      await preferenceService.deletePreference(pref.id)
      const matchesActiveScope =
        scope.kind === 'general'
          ? pref.course_id == null
          : pref.course_id === scope.courseId
      if (matchesActiveScope) {
        hasUserEditedRef.current = false
      }
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
      const targetCourseId = scope.kind === 'course' ? scope.courseId : null

      const saved = await preferenceService.submitPreference({
        user_id: Number(selectedInstructor),
        semester_id: selectedSemester,
        course_id: targetCourseId,
        preferred_days: mappedDays,
        preferred_slots: selectedSlots,
        preferred_rooms: selectedRooms,
      })

      hasUserEditedRef.current = false
      setSavedPreferences((prev) => {
        const normalizedSaved: InstructorPreference = {
          ...saved,
          course_id: saved.course_id !== undefined ? saved.course_id : targetCourseId,
          preferred_days: saved.preferred_days ?? mappedDays,
          preferred_slots: saved.preferred_slots ?? selectedSlots,
          preferred_rooms: saved.preferred_rooms ?? selectedRooms,
        }
        const idx = prev.findIndex(
          (item) => (item.course_id ?? null) === (normalizedSaved.course_id ?? null)
        )
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
    hasUserEditedRef.current = true
    setSelectedDays([])
    setSelectedSlots([])
    setSelectedRooms([])
    setToast(null)
  }

  const activeSemesterLabel =
    SEMESTER_OPTIONS.find((s) => Number(s.value) === selectedSemester)?.label ??
    `Semester ${selectedSemester}`

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Instructor Preferences</h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure semester availability, course-specific preferences, and preferred classrooms for
            the CP-SAT schedule optimizer.
          </p>
        </div>

        {isLockedInstructor && user && (
          <div className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-800">
            <UserCheck className="w-4 h-4 text-blue-600 shrink-0" />
            <span className="font-semibold">{user.full_name}</span>
            <Badge variant="info">{user.department}</Badge>
          </div>
        )}
      </div>

      {!isStandaloneFallback &&
        scope.kind === 'general' &&
        !hasSavedGeneral &&
        courseSpecificCount > 0 && (
          <Alert variant="info" title="Saved Course Preferences Available">
            You have {courseSpecificCount} course-specific preference(s) saved below. Select one to
            edit or save general availability.
          </Alert>
        )}

      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle>Teaching Availability & Classroom Preferences</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Saved preferences load automatically when switching semester or course target.
            </p>
          </div>
          <Badge variant={scope.kind === 'general' ? 'info' : 'gold'}>
            {scope.kind === 'general'
              ? 'General Availability'
              : courseById.get(scope.courseId)?.course_code ?? `Course #${scope.courseId}`}
          </Badge>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Select
              label="Select Instructor"
              options={instructors}
              value={selectedInstructor}
              disabled={isLockedInstructor}
              helperText={
                isLockedInstructor
                  ? 'Locked to your authenticated faculty profile.'
                  : undefined
              }
              onChange={(e) => {
                hasUserEditedRef.current = false
                setSelectedInstructor(e.target.value)
              }}
              data-testid="instructor-select"
            />

            <Select
              label="Academic Semester"
              options={SEMESTER_OPTIONS}
              value={String(selectedSemester)}
              onChange={(e) => {
                hasUserEditedRef.current = false
                setSelectedSemester(Number(e.target.value))
              }}
              data-testid="preference-semester-select"
            />

            <Select
              label="Course Preference Target"
              options={courseOptions}
              value={scope.kind === 'general' ? 'GENERAL' : String(scope.courseId)}
              onChange={(e) => {
                hasUserEditedRef.current = false
                if (e.target.value === 'GENERAL') {
                  setScope({ kind: 'general' })
                } else {
                  setScope({ kind: 'course', courseId: Number(e.target.value) })
                }
              }}
              data-testid="preference-course-select"
            />
          </div>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <label className="block text-xs font-semibold text-slate-700">
                Preferred Days <span className="text-red-500">*</span>
              </label>
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
              Preferred Time Slots <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              {timeSlots.map((timeSlot) => {
                const slot = toSlotKey(timeSlot)
                const isSelected = selectedSlots.includes(slot)
                const isGraduateSlot = timeSlot.level === 'graduate'
                return (
                  <button
                    key={slot}
                    type="button"
                    data-testid={`slot-${slot}`}
                    aria-pressed={isSelected}
                    onClick={() => toggleSlot(slot)}
                    className={`p-2.5 rounded-xl border text-xs flex items-center justify-between gap-1.5 transition-all cursor-pointer text-left focus:outline-none ${
                      isSelected
                        ? 'bg-blue-50 border-blue-600 text-blue-700 font-semibold ring-2 ring-blue-500/20'
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
                    {isGraduateSlot && (
                      <span className="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 text-[10px] font-bold shrink-0">
                        Grad 5000+
                      </span>
                    )}
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
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {rooms.map((room) => {
                const isSelected = selectedRooms.includes(room.room_number)
                const isLab = room.room_type.toLowerCase().includes('lab')
                return (
                  <button
                    key={room.id}
                    type="button"
                    data-testid={`room-chip-${room.room_number}`}
                    aria-pressed={isSelected}
                    onClick={() => toggleRoom(room.room_number)}
                    className={`px-3 py-2 rounded-xl border text-xs flex items-center justify-between gap-2 transition-all cursor-pointer text-left focus:outline-none ${
                      isSelected
                        ? 'bg-blue-50 border-blue-600 text-blue-800 font-semibold ring-2 ring-blue-500/20'
                        : 'border-slate-200 text-slate-700 bg-slate-50 hover:bg-slate-100/80 hover:border-slate-300'
                    }`}
                  >
                    <span className="flex items-center space-x-2 min-w-0">
                      <Building2
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isSelected ? 'text-blue-600' : 'text-slate-400'
                        }`}
                      />
                      <span className="truncate font-semibold">{room.room_number}</span>
                      <span className="text-slate-500 font-normal shrink-0">
                        Cap {room.capacity}
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
        </CardContent>
      </Card>

      <Card data-testid="saved-preferences-list">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <CardTitle>Saved Preferences for Selected Semester</CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                {activeSemesterLabel} ({savedPreferences.length} saved profile
                {savedPreferences.length === 1 ? '' : 's'})
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {savedPreferences.length === 0 ? (
            <p className="text-xs text-slate-500 py-3">
              No saved preferences recorded for this semester yet. Select days and time slots above to
              save your availability.
            </p>
          ) : (
            <div className="space-y-3">
              {savedPreferences.map((pref) => {
                const matchedCourse =
                  pref.course_id != null ? courseById.get(pref.course_id) : undefined
                const courseCode =
                  pref.course_code ??
                  matchedCourse?.course_code ??
                  (pref.course_id != null ? `Course #${pref.course_id}` : null)
                const courseName = pref.course_name ?? matchedCourse?.course_name ?? null
                const isActiveTarget =
                  scope.kind === 'general'
                    ? pref.course_id == null
                    : pref.course_id === scope.courseId
                const dayBadges = normalizeStoredDaysToLabels(pref.preferred_days).map((label) => {
                  const m = label.match(/\(([MTWRF])\)/)
                  return m ? m[1] : label
                })

                return (
                  <div
                    key={pref.id ?? `${pref.user_id}-${pref.semester_id}-${pref.course_id ?? 'gen'}`}
                    className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 rounded-xl border transition-colors ${
                      isActiveTarget
                        ? 'border-blue-300 bg-blue-50/40'
                        : 'border-slate-200 bg-slate-50/60'
                    }`}
                  >
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={pref.course_id == null ? 'info' : 'gold'}>
                          {pref.course_id == null
                            ? 'General Availability'
                            : `${courseCode}${courseName ? ` — ${courseName}` : ''}`}
                        </Badge>
                        {isActiveTarget && <Badge variant="success">Editing</Badge>}
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
