import React, { useEffect, useState } from 'react'
import { Building2 } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Badge, Select } from '../ui'
import { analyticsService, RoomUtilizationReport } from '../../services/analyticsService'

export interface RoomUtilizationChartProps {
  semesterId?: number
}

export const RoomUtilizationChart: React.FC<RoomUtilizationChartProps> = ({
  semesterId = 1,
}) => {
  const [report, setReport] = useState<RoomUtilizationReport | null>(null)
  const [tierFilter, setTierFilter] = useState<string>('ALL')

  useEffect(() => {
    analyticsService.getRoomUtilization(semesterId).then(setReport)
  }, [semesterId])

  if (!report) {
    return (
      <Card>
        <CardContent>
          <p className="text-xs text-slate-500 py-4">Loading classroom utilization metrics...</p>
        </CardContent>
      </Card>
    )
  }

  const filteredRooms = report.rooms.filter((r) =>
    tierFilter === 'ALL' ? true : r.utilization_tier === tierFilter
  )

  return (
    <Card data-testid="room-utilization-chart">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Classroom & Lab Utilization Metrics</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Slot booking density ({report.overall_slot_utilization_pct}%) and seat occupancy ({report.overall_seat_occupancy_pct}%)
            </p>
          </div>
        </div>

        <div className="w-44">
          <Select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            options={[
              { value: 'ALL', label: 'All Utilization Tiers' },
              { value: 'optimal', label: 'Optimal (25% - 74%)' },
              { value: 'heavily_booked', label: 'Heavily Booked (75%+)' },
              { value: 'underutilized', label: 'Underutilized (<25%)' },
            ]}
            data-testid="utilization-tier-filter"
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {filteredRooms.map((room) => (
          <div
            key={room.room_id}
            className="p-3 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-2 text-xs"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-800">{room.room_number}</span>
                <span className="text-slate-500">
                  ({room.room_type} • {room.capacity} seats)
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-slate-600 font-medium">
                  {room.booked_slots_count}/{room.total_available_slots} slots ({room.slot_utilization_pct}%)
                </span>
                <Badge
                  variant={
                    room.utilization_tier === 'optimal'
                      ? 'success'
                      : room.utilization_tier === 'heavily_booked'
                        ? 'warning'
                        : 'neutral'
                  }
                >
                  {room.utilization_tier.replace('_', ' ')}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                  <span>Slot Utilization</span>
                  <span>{room.slot_utilization_pct}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-blue-600 h-full rounded-full"
                    style={{ width: `${Math.min(100, room.slot_utilization_pct)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                  <span>Seat Occupancy (avg {room.average_enrollment} students)</span>
                  <span>{room.seat_occupancy_pct}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-600 h-full rounded-full"
                    style={{ width: `${Math.min(100, room.seat_occupancy_pct)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export default RoomUtilizationChart
