import React, { useEffect, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { scheduleService } from '../../services/scheduleService'
import { transformToCalendarEvents } from '../../utils/scheduleParser'
import { CalendarEventItem } from '../../types/api'
import { Loader2 } from 'lucide-react'

interface ScheduleCalendarProps {
  semesterId?: number
}

const DEPT_LEGEND = [
  { label: 'Computer Science', color: 'bg-blue-600', text: 'text-blue-700' },
  { label: 'Mathematics', color: 'bg-purple-600', text: 'text-purple-700' },
  { label: 'ECE / Physics', color: 'bg-emerald-600', text: 'text-emerald-700' },
  { label: 'Chemistry / Biology', color: 'bg-amber-600', text: 'text-amber-700' },
]

export const ScheduleCalendar: React.FC<ScheduleCalendarProps> = ({ semesterId = 1 }) => {
  const [events, setEvents] = useState<CalendarEventItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const data = await scheduleService.getSchedules(semesterId)
        const formatted = transformToCalendarEvents(data)
        setEvents(formatted)
      } catch (err) {
        console.error('Failed to load schedule events:', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [semesterId])

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-card">
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
              <div key={dept.label} className="flex items-center space-x-1.5 text-xs text-slate-600 font-medium">
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
          events={events}
          eventTextColor="#ffffff"
          height="100%"
          expandRows={true}
        />
      </div>
    </div>
  )
}

export default ScheduleCalendar
