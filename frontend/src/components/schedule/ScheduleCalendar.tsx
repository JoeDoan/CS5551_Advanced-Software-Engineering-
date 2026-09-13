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
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Weekly Schedule Matrix</h2>
          <p className="text-xs text-slate-500">
            Timetable visualization across classrooms and meeting patterns (Monday – Friday)
          </p>
        </div>
        {loading && (
          <div className="flex items-center space-x-2 text-xs text-blue-600 font-medium">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading timetable...</span>
          </div>
        )}
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
          eventColor="#2563eb"
          eventTextColor="#ffffff"
          height="100%"
          expandRows={true}
        />
      </div>
    </div>
  )
}
