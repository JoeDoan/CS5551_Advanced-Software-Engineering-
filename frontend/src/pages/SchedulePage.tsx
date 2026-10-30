import React, { useState, useMemo, useEffect } from 'react'
import { ScheduleCalendar } from '../components/schedule/ScheduleCalendar'
import { ScheduleFilters, ScheduleFilterState } from '../components/schedule/ScheduleFilters'
import { ConflictInspectorPanel } from '../components/schedule/ConflictInspectorPanel'
import { SemesterComparisonModal } from '../components/schedule/SemesterComparisonModal'
import { scheduleService } from '../services/scheduleService'
import { exportScheduleToCSV } from '../utils/exportSchedule'
import { ScheduleEvent } from '../types/api'
import { resolveDepartment } from '../utils/scheduleParser'
import { Filter, Download } from 'lucide-react'
import { Button } from '../components/ui'

const semesters = [
  { id: 1, name: 'Fall 2024' },
  { id: 2, name: 'Spring 2025' },
  { id: 3, name: 'Fall 2025' },
  { id: 4, name: 'Spring 2026' },
  { id: 5, name: 'Fall 2026' },
  { id: 6, name: 'Spring 2027' },
]

export const SchedulePage: React.FC = () => {
  const [selectedSemester, setSelectedSemester] = useState<number>(1)
  const [rawEvents, setRawEvents] = useState<ScheduleEvent[]>([])
  const [isComparisonOpen, setIsComparisonOpen] = useState<boolean>(false)
  const [comparisonEvents, setComparisonEvents] = useState<ScheduleEvent[]>([])
  const [filters, setFilters] = useState<ScheduleFilterState>({
    department: 'ALL',
    search: '',
  })

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

  const filteredEvents = useMemo(() => {
    let list = [...rawEvents]
    if (filters.department && filters.department !== 'ALL') {
      const targetDept = filters.department.toUpperCase()
      list = list.filter(
        (e) => resolveDepartment(e.course_code, e.department) === targetDept
      )
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
  }, [rawEvents, filters])

  const handleExportCSV = () => {
    exportScheduleToCSV(filteredEvents.length > 0 ? filteredEvents : rawEvents, currentSemesterName)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
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

      <ScheduleFilters onFilterChange={setFilters} />

      <ConflictInspectorPanel
        events={filteredEvents.length > 0 ? filteredEvents : rawEvents}
        onOpenComparison={() => setIsComparisonOpen(true)}
      />

      <ScheduleCalendar
        semesterId={selectedSemester}
        filter={filters}
        onEventsLoaded={setRawEvents}
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
