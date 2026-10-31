import React, { useState, useEffect } from 'react'
import { Search, Filter, RotateCcw, User, MapPin } from 'lucide-react'
import { Button } from '../ui'

export interface ScheduleFilterState {
  department: string
  search: string
}

export interface ScheduleFiltersProps {
  onFilterChange: (filters: ScheduleFilterState) => void
  initialDepartment?: string
  initialSearch?: string
  instructors?: string[]
  rooms?: string[]
  selectedInstructor?: string
  selectedRoom?: string
  onInstructorChange?: (instructor: string) => void
  onRoomChange?: (room: string) => void
  extraFiltersActive?: boolean
  onResetExtraFilters?: () => void
}

export const DEPARTMENTS = [
  { value: 'ALL', label: 'All Departments' },
  { value: 'CS', label: 'CS (Computer Science)' },
  { value: 'ECE', label: 'ECE (Electrical & Computer Eng)' },
  { value: 'MATH', label: 'MATH (Mathematics)' },
]

export const ScheduleFilters: React.FC<ScheduleFiltersProps> = ({
  onFilterChange,
  initialDepartment = 'ALL',
  initialSearch = '',
  instructors,
  rooms,
  selectedInstructor = 'ALL',
  selectedRoom = 'ALL',
  onInstructorChange,
  onRoomChange,
  extraFiltersActive = false,
  onResetExtraFilters,
}) => {
  const [department, setDepartment] = useState(initialDepartment)
  const [search, setSearch] = useState(initialSearch)

  useEffect(() => {
    onFilterChange({ department, search })
  }, [department, search, onFilterChange])

  const handleReset = () => {
    setDepartment('ALL')
    setSearch('')
    onInstructorChange?.('ALL')
    onRoomChange?.('ALL')
    onResetExtraFilters?.()
  }

  const isInstructorFiltered = Boolean(selectedInstructor && selectedInstructor !== 'ALL')
  const isRoomFiltered = Boolean(selectedRoom && selectedRoom !== 'ALL')
  const isFiltered =
    department !== 'ALL' ||
    search.trim() !== '' ||
    isInstructorFiltered ||
    isRoomFiltered ||
    extraFiltersActive

  return (
    <div
      data-testid="schedule-filters"
      className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3"
    >
      <div className="flex flex-col xl:flex-row items-stretch xl:items-center justify-between gap-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:flex-wrap items-stretch lg:items-center gap-3 flex-1">
          <div className="relative min-w-[190px]">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Filter className="w-4 h-4" />
            </div>
            <select
              aria-label="Filter by department"
              data-testid="department-filter"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-50 text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
            >
              {DEPARTMENTS.map((dept) => (
                <option key={dept.value} value={dept.value}>
                  {dept.label}
                </option>
              ))}
            </select>
          </div>

          {instructors !== undefined && (
            <div className="relative min-w-[190px]">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <User className="w-4 h-4" />
              </div>
              <select
                aria-label="Filter by instructor"
                data-testid="instructor-filter"
                value={selectedInstructor}
                onChange={(e) => onInstructorChange?.(e.target.value)}
                className="w-full pl-9 pr-8 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-50 text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
              >
                <option value="ALL">All Instructors</option>
                {instructors.map((inst) => (
                  <option key={inst} value={inst}>
                    {inst}
                  </option>
                ))}
              </select>
            </div>
          )}

          {rooms !== undefined && (
            <div className="relative min-w-[170px]">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <MapPin className="w-4 h-4" />
              </div>
              <select
                aria-label="Filter by classroom"
                data-testid="room-filter"
                value={selectedRoom}
                onChange={(e) => onRoomChange?.(e.target.value)}
                className="w-full pl-9 pr-8 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-50 text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
              >
                <option value="ALL">All Classrooms</option>
                {rooms.map((room) => (
                  <option key={room} value={room}>
                    {room}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="relative flex-1 min-w-[220px] sm:col-span-2 lg:col-span-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              aria-label="Search schedule"
              data-testid="schedule-search-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by course code, instructor, or room..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50 text-slate-700 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
            />
          </div>
        </div>

        {isFiltered && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
            data-testid="reset-filters-button"
          >
            Reset Filters
          </Button>
        )}
      </div>
    </div>
  )
}

export default ScheduleFilters
