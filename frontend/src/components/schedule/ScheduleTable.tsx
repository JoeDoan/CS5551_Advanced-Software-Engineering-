import React, { useMemo, useState } from 'react'
import clsx from 'clsx'
import { Clock, MapPin, User, Eye, Loader2 } from 'lucide-react'
import { Badge, Button } from '../ui'
import { ScheduleEvent } from '../../types/api'
import { getDepartmentColors, resolveDepartment } from '../../utils/scheduleParser'

export interface ScheduleTableProps {
  events: ScheduleEvent[]
  loading?: boolean
  onSelectEvent: (event: ScheduleEvent) => void
}

type DayGroupFilter = 'ALL' | 'MWF_GROUP' | 'TR_GROUP'

const DAY_PATTERN_RANK: Record<string, number> = {
  MWF: 1,
  MW: 2,
  WF: 3,
  MF: 4,
  M: 5,
  W: 6,
  F: 7,
  TR: 8,
  T: 9,
  R: 10,
}

const matchesDayGroup = (dayPattern: string, group: DayGroupFilter): boolean => {
  if (group === 'ALL') return true
  const normalized = (dayPattern || '').trim().toUpperCase()
  if (group === 'MWF_GROUP') {
    return /^[MWF]+$/.test(normalized)
  }
  return /^[TR]+$/.test(normalized)
}

export const ScheduleTable: React.FC<ScheduleTableProps> = ({
  events,
  loading = false,
  onSelectEvent,
}) => {
  const [dayGroup, setDayGroup] = useState<DayGroupFilter>('ALL')

  const sortedEvents = useMemo(() => {
    return events
      .filter((ev) => matchesDayGroup(ev.day_pattern, dayGroup))
      .sort((a, b) => {
        const rankA = DAY_PATTERN_RANK[a.day_pattern?.toUpperCase()] ?? 99
        const rankB = DAY_PATTERN_RANK[b.day_pattern?.toUpperCase()] ?? 99
        if (rankA !== rankB) return rankA - rankB
        const patCmp = (a.day_pattern || '').localeCompare(b.day_pattern || '')
        if (patCmp !== 0) return patCmp
        const timeCmp = (a.start_time || '').localeCompare(b.start_time || '')
        if (timeCmp !== 0) return timeCmp
        return (a.course_code || '').localeCompare(b.course_code || '', undefined, {
          numeric: true,
        })
      })
  }, [events, dayGroup])

  const dayGroupOptions: Array<{
    value: DayGroupFilter
    label: string
    testId: string
  }> = [
    { value: 'ALL', label: 'All Days', testId: 'day-group-all' },
    { value: 'MWF_GROUP', label: 'Mon/Wed/Fri', testId: 'day-group-mwf' },
    { value: 'TR_GROUP', label: 'Tue/Thu', testId: 'day-group-tr' },
  ]

  return (
    <div
      data-testid="schedule-table-view"
      className="bg-white rounded-2xl border border-slate-200/90 shadow-card overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Chronological Course Timetable
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Ordered by meeting pattern and start time with zero overlap across classrooms
          </p>
        </div>

        <div className="flex items-center gap-3">
          {loading && (
            <div className="flex items-center space-x-1.5 text-xs text-blue-700 font-medium">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Loading...</span>
            </div>
          )}

          <div className="inline-flex items-center rounded-xl bg-slate-100 p-1 gap-1">
            {dayGroupOptions.map((opt) => (
              <button
                key={opt.value}
                type="button"
                data-testid={opt.testId}
                onClick={() => setDayGroup(opt.value)}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                  dayGroup === opt.value
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {sortedEvents.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-sm font-semibold text-slate-700">
            No scheduled sections match the active filters
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Try switching day groups or resetting your search, instructor, or classroom filters.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-5">Course</th>
                <th className="py-3 px-4">Meeting Days & Time</th>
                <th className="py-3 px-4">Classroom</th>
                <th className="py-3 px-4">Instructor</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {sortedEvents.map((ev) => {
                const dept = resolveDepartment(ev.course_code, ev.department)
                const colors = getDepartmentColors(dept)

                return (
                  <tr
                    key={ev.id}
                    data-testid={`schedule-table-row-${ev.id}`}
                    onClick={() => onSelectEvent(ev)}
                    className="hover:bg-blue-50/40 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-5">
                      <div className="flex items-start space-x-2.5">
                        <span
                          className="w-2.5 h-2.5 rounded-full mt-1 shrink-0"
                          style={{ backgroundColor: colors.bg }}
                        />
                        <div>
                          <div className="font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                            {ev.course_code}
                          </div>
                          <div className="text-slate-500 mt-0.5 line-clamp-1">
                            {ev.course_name}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="inline-flex items-center gap-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-800 font-bold text-[11px]">
                          {ev.day_pattern}
                        </span>
                        <span className="inline-flex items-center text-slate-700 font-medium">
                          <Clock className="w-3.5 h-3.5 text-slate-400 mr-1" />
                          {ev.start_time} – {ev.end_time}
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center font-semibold text-slate-800">
                        <MapPin className="w-3.5 h-3.5 text-emerald-600 mr-1.5" />
                        {ev.room_number}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center text-slate-700 font-medium">
                        <User className="w-3.5 h-3.5 text-slate-400 mr-1.5" />
                        {ev.instructor_name}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <Badge
                        variant={ev.status === 'confirmed' ? 'success' : 'gold'}
                        dot
                      >
                        {ev.status}
                      </Badge>
                    </td>

                    <td className="py-3.5 px-5 text-right whitespace-nowrap">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        leftIcon={<Eye className="w-3.5 h-3.5" />}
                        data-testid={`schedule-row-details-${ev.id}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelectEvent(ev)
                        }}
                      >
                        Details
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default ScheduleTable
