import React, { useState } from 'react'
import { ScheduleCalendar } from '../components/schedule/ScheduleCalendar'
import { Filter } from 'lucide-react'

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Master Schedule Matrix</h1>
          <p className="text-sm text-slate-500 mt-1">
            Browse and inspect optimized timetables across all 6 simulated academic semesters.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-white px-3 py-2 rounded-xl border border-slate-200 shadow-sm text-xs">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="font-semibold text-slate-600">Semester:</span>
            <select
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
        </div>
      </div>

      <ScheduleCalendar semesterId={selectedSemester} />
    </div>
  )
}
