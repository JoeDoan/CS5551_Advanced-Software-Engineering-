import React, { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Alert, Badge, Card, CardContent, CardHeader, CardTitle, Select } from '../ui'
import {
  BottleneckReport,
  RiskTier,
  courseLabel,
  errorMessage,
  insightsService,
} from '../../services/insightsService'

const TIER_VARIANT: Record<RiskTier, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  watch: 'info',
  ok: 'success',
}

const TIER_LABEL: Record<RiskTier, string> = {
  critical: 'Critical',
  high: 'High',
  watch: 'Watch',
  ok: 'OK',
}

export const BottleneckBoard: React.FC = () => {
  const [report, setReport] = useState<BottleneckReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tier, setTier] = useState<string>('ALL')

  useEffect(() => {
    insightsService
      .getBottlenecks()
      .then(setReport)
      .catch((e) => setError(errorMessage(e)))
  }, [])

  if (error) {
    return (
      <Alert variant="danger" title="Bottleneck report unavailable" data-testid="bottleneck-error">
        {error}
      </Alert>
    )
  }
  if (!report) {
    return <p className="text-xs text-slate-500 py-4">Loading bottleneck analysis...</p>
  }

  const rows = report.items.filter((i) => (tier === 'ALL' ? true : i.risk_tier === tier))
  const { summary, meta } = report

  return (
    <Card data-testid="bottleneck-board">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Room-Capacity Bottlenecks</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Forecast demand for {meta.target_semester_name} against the largest compatible room
            </p>
          </div>
        </div>
        {meta.is_synthetic && <Badge variant="warning">Synthetic history</Badge>}
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="tier-counts">
          {(Object.keys(TIER_LABEL) as RiskTier[]).map((t) => (
            <div key={t} className="rounded-xl border border-slate-200 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">
                {TIER_LABEL[t]}
              </div>
              <div className="text-2xl font-bold text-slate-900" data-testid={`tier-count-${t}`}>
                {summary.tier_counts[t]}
              </div>
            </div>
          ))}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-800 mb-2">
            Capacity cliffs (growth before no room fits)
          </h3>
          <p className="text-[11px] text-slate-500 mb-2">
            Deterministic arithmetic on today's plan, not a forecast: largest compatible room
            capacity divided by expected enrollment, minus 1.
          </p>
          <ul className="space-y-1.5" data-testid="cliff-list">
            {summary.tightest_cliffs.map((c) => (
              <li key={c.course_id} className="flex items-center justify-between text-xs">
                <span className="text-slate-800">
                  <span className="font-semibold">{courseLabel(c.course_code, c.course_name)}</span>
                  <span className="text-slate-500">
                    {' '}
                    ({c.expected_enrollment} seats needed, {c.largest_compatible_room} holds{' '}
                    {c.max_room_capacity})
                  </span>
                </span>
                <Badge variant={c.capacity_cliff_pct < 10 ? 'danger' : 'warning'}>
                  +{c.capacity_cliff_pct}%
                </Badge>
              </li>
            ))}
          </ul>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="seat-band-table">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-4">Seats needed</th>
                <th className="py-2 pr-4">Courses (forecast)</th>
                <th className="py-2 pr-4">Rooms that can host</th>
              </tr>
            </thead>
            <tbody>
              {summary.seat_band_pressure.map((b) => (
                <tr key={b.min_seats} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{b.min_seats}+</td>
                  <td className="py-2 pr-4">{b.courses_needing}</td>
                  <td className="py-2 pr-4">{b.rooms_available}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="w-48">
          <Select
            label="Risk tier"
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            options={[
              { value: 'ALL', label: 'All tiers' },
              { value: 'critical', label: 'Critical' },
              { value: 'high', label: 'High' },
              { value: 'watch', label: 'Watch' },
              { value: 'ok', label: 'OK' },
            ]}
            data-testid="bottleneck-tier-filter"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="bottleneck-table">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-3">Course</th>
                <th className="py-2 pr-3">Forecast (95% high)</th>
                <th className="py-2 pr-3">Largest room</th>
                <th className="py-2 pr-3">Headroom</th>
                <th className="py-2 pr-3">P(overflow)</th>
                <th className="py-2 pr-3">Tier</th>
                <th className="py-2">Suggested remedy</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((i) => (
                <tr key={i.course_id} className="border-b border-slate-100 align-top">
                  <td className="py-2 pr-3 font-medium text-slate-800">{i.course_code}</td>
                  <td className="py-2 pr-3">
                    {i.forecast} ({i.forecast_hi95})
                  </td>
                  <td className="py-2 pr-3">
                    {i.largest_compatible_room} ({i.max_room_capacity})
                  </td>
                  <td className="py-2 pr-3">{i.headroom_pct}%</td>
                  <td className="py-2 pr-3">{Math.round(i.overflow_probability * 100)}%</td>
                  <td className="py-2 pr-3">
                    <Badge variant={TIER_VARIANT[i.risk_tier]}>{TIER_LABEL[i.risk_tier]}</Badge>
                  </td>
                  <td className="py-2 text-slate-600">
                    {i.remedy ? (
                      <>
                        {i.remedy.detail}
                        {!i.remedy.solver_confirmed && (
                          <span className="block text-[10px] text-slate-400">
                            Not yet confirmed by the solver. Verify in the What-If tab.
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-slate-400">None needed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default BottleneckBoard
