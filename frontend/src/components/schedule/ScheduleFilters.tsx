import React, { useState, useEffect } from 'react'
import { Search, Filter, RotateCcw } from 'lucide-react'
import { Button } from '../ui'

export interface ScheduleFilterState {
  department: string
  search: string
}

export interface ScheduleFiltersProps {
  onFilterChange: (filters: ScheduleFilterState) => void
  initialDepartment?: string
  initialSearch?: string
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
}) => {
  const [department, setDepartment] = useState(initialDepartment)
  const [search, setSearch] = useState(initialSearch)

  useEffect(() => {
    onFilterChange({ department, search })
  }, [department, search, onFilterChange])

  const handleReset = () => {
    setDepartment('ALL')
    setSearch('')
  }

  const isFiltered = department !== 'ALL' || search.trim() !== ''

  return (
    <div
      data-testid="schedule-filters"
      className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3"
    >
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-1">
          {/* Department Filter */}
          <div className="relative min-w-[200px]">
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

          {/* Search Input */}
          <div className="relative flex-1">
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

        {/* Reset Filter Button */}
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
