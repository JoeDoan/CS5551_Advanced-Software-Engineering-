import React, { useEffect, useMemo, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { EventClickArg, EventContentArg } from '@fullcalendar/core'
import { Info, Loader2 } from 'lucide-react'
import { scheduleService } from '../../services/scheduleService'
import { transformToCalendarEvents, resolveDepartment } from '../../utils/scheduleParser'
import { CalendarEventItem, ScheduleEvent } from '../../types/api'
import { EventDetailModal } from './EventDetailModal'

export interface ScheduleCalendarProps {
  semesterId?: number
  filter?: { department?: string; search?: string }
  onEventsLoaded?: (rawEvents: ScheduleEvent[]) => void
  eventsData?: ScheduleEvent[]
  loadingOverride?: boolean
  onSelectEvent?: (event: ScheduleEvent) => void
  hasEntityFilter?: boolean
}

const DEPT_LEGEND = [
  { label: 'Computer Science', color: 'bg-blue-600', text: 'text-blue-700' },
  { label: 'Mathematics', color: 'bg-purple-600', text: 'text-purple-700' },
  { label: 'ECE / Physics', color: 'bg-emerald-600', text: 'text-emerald-700' },
  { label: 'Chemistry / Biology', color: 'bg-amber-600', text: 'text-amber-700' },
]

export const ScheduleCalendar: React.FC<ScheduleCalendarProps> = ({
  semesterId = 1,
  filter,
  onEventsLoaded,
  eventsData,
  loadingOverride,
  onSelectEvent,
  hasEntityFilter = false,
}) => {
  const isControlled = eventsData !== undefined
  const [internalRawEvents, setInternalRawEvents] = useState<ScheduleEvent[]>([])
  const [internalLoading, setInternalLoading] = useState<boolean>(!isControlled)
  const [selectedEvent, setSelectedEvent] = useState<ScheduleEvent | null>(null)

  useEffect(() => {
    if (isControlled) {
      return
    }
    let active = true
    async function loadData() {
      setInternalLoading(true)
      try {
        const data = await scheduleService.getSchedules(semesterId)
        if (!active) return
        setInternalRawEvents(data)
        onEventsLoaded?.(data)
      } catch (err) {
        console.error('Failed to load schedule events:', err)
        if (!active) return
        setInternalRawEvents([])
        onEventsLoaded?.([])
      } finally {
        if (active) {
          setInternalLoading(false)
        }
      }
    }
    loadData()
    return () => {
      active = false
    }
  }, [isControlled, semesterId, onEventsLoaded])

  const sourceEvents = isControlled ? eventsData : internalRawEvents
  const loading = isControlled ? Boolean(loadingOverride) : internalLoading

  const filteredScheduleEvents = useMemo(() => {
    let filtered = [...sourceEvents]
    if (filter?.department && filter.department !== 'ALL') {
      const targetDept = filter.department.toUpperCase()
      filtered = filtered.filter(
        (e) => resolveDepartment(e.course_code, e.department) === targetDept
      )
    }
    if (filter?.search && filter.search.trim() !== '') {
      const q = filter.search.toLowerCase()
      filtered = filtered.filter(
        (e) =>
          e.course_code.toLowerCase().includes(q) ||
          e.course_name.toLowerCase().includes(q) ||
          e.instructor_name.toLowerCase().includes(q) ||
          e.room_number.toLowerCase().includes(q)
      )
    }
    return filtered
  }, [sourceEvents, filter])

  const calendarEvents: CalendarEventItem[] = useMemo(
    () => transformToCalendarEvents(filteredScheduleEvents),
    [filteredScheduleEvents]
  )

  const handleEventClick = (clickInfo: EventClickArg) => {
    const rawId = Number(clickInfo.event.id.split('-')[0])
    const found = sourceEvents.find((item) => item.id === rawId)
    if (!found) return
    if (onSelectEvent) {
      onSelectEvent(found)
    } else {
      setSelectedEvent(found)
    }
  }

  const renderEventContent = (eventInfo: EventContentArg) => {
    const props = eventInfo.event.extendedProps as {
      course_code?: string
      room?: string
      instructor?: string
    }
    return (
      <div className="px-1.5 py-0.5 overflow-hidden leading-tight text-white">
        <div className="font-bold text-[11px] truncate">
          {props.course_code || eventInfo.event.title}
        </div>
        {props.room && (
          <div className="text-[10px] opacity-95 truncate">{props.room}</div>
        )}
        {props.instructor && (
          <div className="text-[10px] opacity-85 truncate">{props.instructor}</div>
        )}
      </div>
    )
  }

  const showDensityTip = filteredScheduleEvents.length > 15 && !hasEntityFilter

  return (
    <div
      data-testid="schedule-calendar-view"
      className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-card"
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-5 pb-4 border-b border-slate-100">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Weekly Schedule Matrix</h2>
          <p className="text-xs text-slate-500">
            Timetable visualization across classrooms and meeting patterns (Monday – Friday)
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex flex-wrap items-center gap-3">
            {DEPT_LEGEND.map((dept) => (
              <div
                key={dept.label}
                className="flex items-center space-x-1.5 text-xs text-slate-600 font-medium"
              >
                <span className={`w-2.5 h-2.5 rounded-full ${dept.color} shadow-sm`} />
                <span>{dept.label}</span>
              </div>
            ))}
          </div>

          {loading && (
            <div className="flex items-center space-x-2 text-xs text-umkc-blue-700 font-medium">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading...</span>
            </div>
          )}
        </div>
      </div>

      {showDensityTip && (
        <div
          data-testid="calendar-density-tip"
          className="mb-4 flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50/70 px-3.5 py-2.5 text-xs text-blue-900"
        >
          <Info className="w-4 h-4 text-blue-600 shrink-0" />
          <span>
            Displaying {filteredScheduleEvents.length} concurrent sections across campus. Filter by{' '}
            <strong className="font-semibold">Instructor</strong> or{' '}
            <strong className="font-semibold">Classroom</strong> above, or switch to{' '}
            <strong className="font-semibold">Table View</strong> or{' '}
            <strong className="font-semibold">Room Matrix</strong> for a full-campus overview.
          </span>
        </div>
      )}

      <div className="h-[680px]">
        <FullCalendar
          plugins={[timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            left: '',
            center: 'title',
            right: '',
          }}
          weekends={false}
          allDaySlot={false}
          slotMinTime="08:00:00"
          slotMaxTime="21:00:00"
          slotDuration="00:30:00"
          slotEventOverlap={false}
          events={calendarEvents}
          eventClick={handleEventClick}
          eventContent={renderEventContent}
          eventTextColor="#ffffff"
          height="100%"
          expandRows={true}
        />
      </div>

      {!onSelectEvent && (
        <EventDetailModal
          isOpen={selectedEvent !== null}
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  )
}

export default ScheduleCalendar
