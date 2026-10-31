import React, { useState, useMemo, useEffect } from 'react'
import clsx from 'clsx'
import {
  Filter,
  Download,
  List,
  LayoutGrid,
  Calendar as CalendarIcon,
  UserCheck,
  Building2,
} from 'lucide-react'
import { ScheduleCalendar } from '../components/schedule/ScheduleCalendar'
import { ScheduleTable } from '../components/schedule/ScheduleTable'
import { ScheduleRoomMatrix } from '../components/schedule/ScheduleRoomMatrix'
import { ScheduleFilters, ScheduleFilterState } from '../components/schedule/ScheduleFilters'
import { ConflictInspectorPanel } from '../components/schedule/ConflictInspectorPanel'
import { SemesterComparisonModal } from '../components/schedule/SemesterComparisonModal'
import { EventDetailModal } from '../components/schedule/EventDetailModal'
import { scheduleService } from '../services/scheduleService'
import { exportScheduleToCSV } from '../utils/exportSchedule'
import { ScheduleEvent } from '../types/api'
import { resolveDepartment } from '../utils/scheduleParser'
import { useAuth } from '../context/AuthContext'
import { Button } from '../components/ui'

export type ScheduleViewMode = 'table' | 'matrix' | 'calendar'
export type ScheduleScopeMode = 'mine' | 'all'

const semesters = [
  { id: 1, name: 'Fall 2024' },
  { id: 2, name: 'Spring 2025' },
  { id: 3, name: 'Fall 2025' },
  { id: 4, name: 'Spring 2026' },
  { id: 5, name: 'Fall 2026' },
  { id: 6, name: 'Spring 2027' },
]

export const SchedulePage: React.FC = () => {
  const { user, isStandaloneFallback } = useAuth()
  const isInstructorSession = !isStandaloneFallback && user?.role === 'instructor'

  const [selectedSemester, setSelectedSemester] = useState<number>(1)
  const [rawEvents, setRawEvents] = useState<ScheduleEvent[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [viewMode, setViewMode] = useState<ScheduleViewMode>(() =>
    isInstructorSession ? 'calendar' : 'table'
  )
  const [scopeMode, setScopeMode] = useState<ScheduleScopeMode>(() =>
    isInstructorSession ? 'mine' : 'all'
  )
  const [hasCustomViewSelection, setHasCustomViewSelection] = useState<boolean>(false)
  const [selectedInstructor, setSelectedInstructor] = useState<string>('ALL')
  const [selectedRoom, setSelectedRoom] = useState<string>('ALL')
  const [selectedEvent, setSelectedEvent] = useState<ScheduleEvent | null>(null)
  const [isComparisonOpen, setIsComparisonOpen] = useState<boolean>(false)
  const [comparisonEvents, setComparisonEvents] = useState<ScheduleEvent[]>([])
  const [filters, setFilters] = useState<ScheduleFilterState>({
    department: 'ALL',
    search: '',
  })

  useEffect(() => {
    if (hasCustomViewSelection) return
    if (isInstructorSession) {
      setScopeMode('mine')
      setViewMode('calendar')
    } else {
      setScopeMode('all')
      setViewMode('table')
    }
  }, [isInstructorSession, hasCustomViewSelection])

  useEffect(() => {
    let active = true
    setLoading(true)
    scheduleService
      .getSchedules(selectedSemester)
      .then((events) => {
        if (active) {
          setRawEvents(events)
        }
      })
      .catch(() => {
        if (active) {
          setRawEvents([])
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [selectedSemester])

  const currentSemesterName = useMemo(() => {
    return semesters.find((s) => s.id === selectedSemester)?.name || `Semester_${selectedSemester}`
  }, [selectedSemester])

  const comparisonSemesterId = selectedSemester < 6 ? selectedSemester + 1 : 1
  const comparisonSemesterName = useMemo(() => {
    return (
      semesters.find((s) => s.id === comparisonSemesterId)?.name ||
      `Semester_${comparisonSemesterId}`
    )
  }, [comparisonSemesterId])

  useEffect(() => {
    if (!isComparisonOpen) return
    let active = true
    scheduleService.getBySemester(comparisonSemesterId).then((events) => {
      if (active) {
        setComparisonEvents(events)
      }
    })
    return () => {
      active = false
    }
  }, [isComparisonOpen, comparisonSemesterId])

  const availableInstructors = useMemo(() => {
    const names = new Set<string>()
    for (const ev of rawEvents) {
      if (ev.instructor_name) {
        names.add(ev.instructor_name)
      }
    }
    if (selectedInstructor !== 'ALL') {
      names.add(selectedInstructor)
    }
    return Array.from(names).sort((a, b) => a.localeCompare(b))
  }, [rawEvents, selectedInstructor])

  const availableRooms = useMemo(() => {
    const rooms = new Set<string>()
    for (const ev of rawEvents) {
      if (ev.room_number) {
        rooms.add(ev.room_number)
      }
    }
    if (selectedRoom !== 'ALL') {
      rooms.add(selectedRoom)
    }
    return Array.from(rooms).sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true })
    )
  }, [rawEvents, selectedRoom])

  const filteredEvents = useMemo(() => {
    let list = [...rawEvents]

    if (isInstructorSession && scopeMode === 'mine' && user) {
      const normalizedUserFullName = user.full_name.trim().toLowerCase()
      list = list.filter((e) => {
        const matchesId =
          user.linked_user_id !== null &&
          (e.user_id === user.linked_user_id || e.instructor_id === user.linked_user_id)
        const matchesName =
          (e.instructor_name || '').trim().toLowerCase() === normalizedUserFullName
        return matchesId || matchesName
      })
    }

    if (filters.department && filters.department !== 'ALL') {
      const targetDept = filters.department.toUpperCase()
      list = list.filter(
        (e) => resolveDepartment(e.course_code, e.department) === targetDept
      )
    }

    if (selectedInstructor !== 'ALL') {
      list = list.filter((e) => e.instructor_name === selectedInstructor)
    }

    if (selectedRoom !== 'ALL') {
      list = list.filter((e) => e.room_number === selectedRoom)
    }

    if (filters.search && filters.search.trim() !== '') {
      const q = filters.search.toLowerCase()
      list = list.filter(
        (e) =>
          (e.course_code || '').toLowerCase().includes(q) ||
          (e.course_name || '').toLowerCase().includes(q) ||
          (e.instructor_name || '').toLowerCase().includes(q) ||
          (e.room_number || '').toLowerCase().includes(q)
      )
    }

    return list
  }, [
    rawEvents,
    isInstructorSession,
    scopeMode,
    user,
    filters,
    selectedInstructor,
    selectedRoom,
  ])

  const handleInstructorFilterChange = (instructor: string) => {
    setSelectedInstructor(instructor)
    if (isInstructorSession && instructor !== 'ALL' && scopeMode === 'mine') {
      setHasCustomViewSelection(true)
      setScopeMode('all')
    }
  }

  const handleExportCSV = () => {
    exportScheduleToCSV(
      filteredEvents.length > 0 ? filteredEvents : rawEvents,
      currentSemesterName
    )
  }

  const matrixRooms = useMemo(() => {
    if (selectedRoom !== 'ALL') return [selectedRoom]
    if (
      (isInstructorSession && scopeMode === 'mine') ||
      selectedInstructor !== 'ALL'
    ) {
      return undefined
    }
    return availableRooms
  }, [
    selectedRoom,
    isInstructorSession,
    scopeMode,
    selectedInstructor,
    availableRooms,
  ])

  const hasEntityFilter =
    (isInstructorSession && scopeMode === 'mine') ||
    selectedInstructor !== 'ALL' ||
    selectedRoom !== 'ALL'

  const viewOptions: Array<{
    mode: ScheduleViewMode
    label: string
    testId: string
    icon: React.ReactNode
  }> = [
    {
      mode: 'table',
      label: 'Table View',
      testId: 'view-mode-table',
      icon: <List className="w-3.5 h-3.5" />,
    },
    {
      mode: 'matrix',
      label: 'Room Matrix',
      testId: 'view-mode-matrix',
      icon: <LayoutGrid className="w-3.5 h-3.5" />,
    },
    {
      mode: 'calendar',
      label: 'Weekly Calendar',
      testId: 'view-mode-calendar',
      icon: <CalendarIcon className="w-3.5 h-3.5" />,
    },
  ]

  return (
    <div className="space-y-5">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Master Schedule Matrix</h1>
          <p className="text-sm text-slate-500 mt-1">
            Browse and inspect optimized timetables across all 6 simulated academic semesters.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 bg-white px-3 py-2 rounded-xl border border-slate-200 shadow-sm text-xs">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="font-semibold text-slate-600">Semester:</span>
            <select
              aria-label="Select semester"
              data-testid="semester-select"
              value={selectedSemester}
              onChange={(e) => setSelectedSemester(Number(e.target.value))}
              className="bg-transparent font-semibold text-blue-700 outline-none cursor-pointer"
            >
              {semesters.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            leftIcon={<Download className="w-4 h-4" />}
            data-testid="export-csv-button"
          >
            Export CSV
          </Button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white px-4 py-3 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          {isInstructorSession && (
            <div className="inline-flex items-center rounded-xl bg-slate-100 p-1 gap-1">
              <button
                type="button"
                data-testid="schedule-scope-mine"
                onClick={() => {
                  setHasCustomViewSelection(true)
                  setScopeMode('mine')
                  setSelectedInstructor('ALL')
                }}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                  scopeMode === 'mine'
                    ? 'bg-umkc-blue-700 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>My Teaching Schedule</span>
              </button>
              <button
                type="button"
                data-testid="schedule-scope-all"
                onClick={() => {
                  setHasCustomViewSelection(true)
                  setScopeMode('all')
                }}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                  scopeMode === 'all'
                    ? 'bg-umkc-blue-700 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>All Department Schedule</span>
              </button>
            </div>
          )}

          <span
            data-testid="schedule-section-count"
            className="inline-flex items-center px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700"
          >
            Showing {filteredEvents.length} of {rawEvents.length} sections
          </span>
        </div>

        <div className="inline-flex items-center rounded-xl bg-slate-100 p-1 gap-1 self-start md:self-auto">
          {viewOptions.map((opt) => (
            <button
              key={opt.mode}
              type="button"
              data-testid={opt.testId}
              onClick={() => {
                setHasCustomViewSelection(true)
                setViewMode(opt.mode)
              }}
              className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                viewMode === opt.mode
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              )}
            >
              {opt.icon}
              <span>{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      <ScheduleFilters
        onFilterChange={setFilters}
        instructors={availableInstructors}
        rooms={availableRooms}
        selectedInstructor={selectedInstructor}
        selectedRoom={selectedRoom}
        onInstructorChange={handleInstructorFilterChange}
        onRoomChange={setSelectedRoom}
      />

      <ConflictInspectorPanel
        events={filteredEvents}
        onOpenComparison={() => setIsComparisonOpen(true)}
      />

      {viewMode === 'table' && (
        <ScheduleTable
          events={filteredEvents}
          loading={loading}
          onSelectEvent={setSelectedEvent}
        />
      )}

      {viewMode === 'matrix' && (
        <ScheduleRoomMatrix
          events={filteredEvents}
          rooms={matrixRooms}
          loading={loading}
          onSelectEvent={setSelectedEvent}
        />
      )}

      {viewMode === 'calendar' && (
        <ScheduleCalendar
          semesterId={selectedSemester}
          eventsData={filteredEvents}
          loadingOverride={loading}
          onSelectEvent={setSelectedEvent}
          hasEntityFilter={hasEntityFilter}
        />
      )}

      <EventDetailModal
        isOpen={selectedEvent !== null}
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />

      <SemesterComparisonModal
        isOpen={isComparisonOpen}
        onClose={() => setIsComparisonOpen(false)}
        baseSemesterLabel={`Semester ${selectedSemester} (${currentSemesterName})`}
        targetSemesterLabel={`Semester ${comparisonSemesterId} (${comparisonSemesterName})`}
        baseEvents={rawEvents}
        targetEvents={comparisonEvents}
      />
    </div>
  )
}

export default SchedulePage
