import React, { useMemo } from 'react'
import { Loader2 } from 'lucide-react'
import { ScheduleEvent } from '../../types/api'
import { getDepartmentColors, resolveDepartment } from '../../utils/scheduleParser'

export interface ScheduleRoomMatrixProps {
  events: ScheduleEvent[]
  rooms?: string[]
  loading?: boolean
  onSelectEvent: (event: ScheduleEvent) => void
}

interface MatrixSlotRow {
  key: string
  dayPattern: string
  startTime: string
  endTime: string
}

const DAY_PATTERN_RANK: Record<string, number> = {
  MWF: 1,
  MW: 2,
  WF: 3,
  MF: 4,
  MR: 5,
  M: 6,
  W: 7,
  F: 8,
  TR: 9,
  T: 10,
  R: 11,
}

const formatLastName = (fullName: string): string => {
  const cleaned = (fullName || '').trim()
  if (!cleaned) return ''
  const tokens = cleaned.split(/\s+/)
  return tokens[tokens.length - 1]
}

const makeSlotKey = (dayPattern: string, startTime: string, endTime: string): string =>
  `${dayPattern}|${startTime}|${endTime}`

export const ScheduleRoomMatrix: React.FC<ScheduleRoomMatrixProps> = ({
  events,
  rooms,
  loading = false,
  onSelectEvent,
}) => {
  const columns = useMemo(() => {
    const roomSet = new Set<string>(rooms && rooms.length > 0 ? rooms : [])
    for (const ev of events) {
      if (ev.room_number) {
        roomSet.add(ev.room_number)
      }
    }
    return Array.from(roomSet).sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true })
    )
  }, [events, rooms])

  const slotRows = useMemo(() => {
    const byKey = new Map<string, MatrixSlotRow>()
    for (const ev of events) {
      const key = makeSlotKey(ev.day_pattern, ev.start_time, ev.end_time)
      if (!byKey.has(key)) {
        byKey.set(key, {
          key,
          dayPattern: ev.day_pattern,
          startTime: ev.start_time,
          endTime: ev.end_time,
        })
      }
    }
    return Array.from(byKey.values()).sort((a, b) => {
      const rankA = DAY_PATTERN_RANK[a.dayPattern?.toUpperCase()] ?? 99
      const rankB = DAY_PATTERN_RANK[b.dayPattern?.toUpperCase()] ?? 99
      if (rankA !== rankB) return rankA - rankB
      const patCmp = a.dayPattern.localeCompare(b.dayPattern)
      if (patCmp !== 0) return patCmp
      const startCmp = a.startTime.localeCompare(b.startTime)
      if (startCmp !== 0) return startCmp
      return a.endTime.localeCompare(b.endTime)
    })
  }, [events])

  const cellIndex = useMemo(() => {
    const index = new Map<string, ScheduleEvent[]>()
    for (const ev of events) {
      const cellKey = `${makeSlotKey(ev.day_pattern, ev.start_time, ev.end_time)}::${ev.room_number}`
      const existing = index.get(cellKey)
      if (existing) {
        existing.push(ev)
      } else {
        index.set(cellKey, [ev])
      }
    }
    return index
  }, [events])

  return (
    <div
      data-testid="schedule-room-matrix-view"
      className="bg-white rounded-2xl border border-slate-200/90 shadow-card overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Classroom × Time-Slot Occupancy Matrix
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspect room availability across meeting blocks and click any assigned course to view details
          </p>
        </div>

        {loading && (
          <div className="flex items-center space-x-1.5 text-xs text-blue-700 font-medium">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Loading...</span>
          </div>
        )}
      </div>

      {slotRows.length === 0 || columns.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-sm font-semibold text-slate-700">
            No classroom occupancy cells match the active filters
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Adjust department, instructor, classroom, or search filters to inspect room availability.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-600">
                <th className="sticky left-0 z-10 bg-slate-50 py-3 px-4 text-left border-r border-slate-200 min-w-[165px]">
                  Time Slot
                </th>
                {columns.map((room) => (
                  <th
                    key={room}
                    className="py-3 px-3 text-center min-w-[125px] border-r border-slate-100 last:border-r-0"
                  >
                    {room}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {slotRows.map((slot) => (
                <tr key={slot.key} className="hover:bg-slate-50/50">
                  <td className="sticky left-0 z-10 bg-white py-2.5 px-4 border-r border-slate-200 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-800 font-bold text-[11px]">
                        {slot.dayPattern}
                      </span>
                      <span className="font-semibold text-slate-700">
                        {slot.startTime} – {slot.endTime}
                      </span>
                    </div>
                  </td>

                  {columns.map((room) => {
                    const cellEvents = cellIndex.get(`${slot.key}::${room}`) || []

                    return (
                      <td
                        key={`${slot.key}::${room}`}
                        className="p-2 text-center align-middle border-r border-slate-100 last:border-r-0"
                      >
                        {cellEvents.length === 0 ? (
                          <span className="inline-block px-2 py-1 rounded-lg text-[11px] font-medium text-slate-300 select-none">
                            Open
                          </span>
                        ) : (
                          <div className="flex flex-col gap-1">
                            {cellEvents.map((ev) => {
                              const dept = resolveDepartment(ev.course_code, ev.department)
                              const colors = getDepartmentColors(dept)
                              const lastName = formatLastName(ev.instructor_name)

                              return (
                                <button
                                  key={ev.id}
                                  type="button"
                                  data-testid={`matrix-event-chip-${ev.id}`}
                                  onClick={() => onSelectEvent(ev)}
                                  style={{
                                    backgroundColor: colors.bg,
                                    borderColor: colors.border,
                                  }}
                                  className="w-full px-2 py-1.5 rounded-lg border text-white text-left shadow-sm hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-opacity"
                                >
                                  <div className="font-bold text-[11px] leading-tight truncate">
                                    {ev.course_code}
                                  </div>
                                  {lastName && (
                                    <div className="text-[10px] opacity-90 leading-tight truncate mt-0.5">
                                      {lastName}
                                    </div>
                                  )}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default ScheduleRoomMatrix
