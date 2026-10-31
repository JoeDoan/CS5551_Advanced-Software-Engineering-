import React, { useEffect, useMemo, useState } from 'react'
import { LineChart } from 'lucide-react'
import { Alert, Badge, Card, CardContent, CardHeader, CardTitle, Select } from '../ui'
import {
  CourseForecast,
  EnrollmentForecast,
  courseLabel,
  errorMessage,
  insightsService,
} from '../../services/insightsService'

const W = 640
const H = 240
const PAD = { l: 48, r: 24, t: 16, b: 36 }

export const shortSemester = (name: string): string =>
  name.replace(/\s(\d{2})(\d{2})$/, " '$2")

export const ForecastChart: React.FC<{ course: CourseForecast; targetName: string }> = ({
  course,
  targetName,
}) => {
  const n = course.history.length
  const values = [...course.history.map((h) => h.enrolled), course.interval_95[1]]
  const yMax = Math.max(...values) * 1.1
  const x = (i: number) => PAD.l + (i * (W - PAD.l - PAD.r)) / n
  const y = (v: number) => H - PAD.b - (v / yMax) * (H - PAD.t - PAD.b)
  const hist = course.history.map((h, i) => `${x(i)},${y(h.enrolled)}`).join(' ')
  const last = course.history[n - 1]
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(yMax * f))

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Enrollment history and forecast for ${course.course_code}`}
      className="w-full h-auto"
      data-testid="forecast-chart"
    >
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="#e2e8f0" />
          <text x={PAD.l - 8} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#64748b">
            {t}
          </text>
        </g>
      ))}
      <rect
        x={x(n) - 10}
        y={y(course.interval_95[1])}
        width={20}
        height={y(course.interval_95[0]) - y(course.interval_95[1])}
        fill="#bfdbfe"
        opacity={0.6}
      />
      <rect
        x={x(n) - 10}
        y={y(course.interval_80[1])}
        width={20}
        height={y(course.interval_80[0]) - y(course.interval_80[1])}
        fill="#60a5fa"
        opacity={0.7}
      />
      <polyline points={hist} fill="none" stroke="#1d4ed8" strokeWidth="2" />
      <line
        x1={x(n - 1)}
        y1={y(last.enrolled)}
        x2={x(n)}
        y2={y(course.forecast)}
        stroke="#d97706"
        strokeWidth="2"
        strokeDasharray="5 4"
      />
      {course.history.map((h, i) => (
        <g key={h.semester_id}>
          <circle cx={x(i)} cy={y(h.enrolled)} r="3.5" fill="#1d4ed8" />
          <text x={x(i)} y={H - 14} textAnchor="middle" fontSize="10" fill="#64748b">
            {shortSemester(h.semester_name)}
          </text>
        </g>
      ))}
      <circle cx={x(n)} cy={y(course.forecast)} r="5" fill="#d97706" />
      <text x={x(n)} y={H - 14} textAnchor="middle" fontSize="10" fill="#b45309" fontWeight="bold">
        {shortSemester(targetName)}
      </text>
    </svg>
  )
}

export const ForecastPanel: React.FC = () => {
  const [data, setData] = useState<EnrollmentForecast | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [courseId, setCourseId] = useState<number | null>(null)

  useEffect(() => {
    insightsService
      .getForecast()
      .then((d) => {
        setData(d)
        setCourseId(d.courses[0]?.course_id ?? null)
      })
      .catch((e) => setError(errorMessage(e)))
  }, [])

  const course = useMemo(
    () => data?.courses.find((c) => c.course_id === courseId) ?? null,
    [data, courseId]
  )

  if (error) {
    return (
      <Alert variant="danger" title="Forecast unavailable" data-testid="forecast-error">
        {error}
      </Alert>
    )
  }
  if (!data || !course) {
    return <p className="text-xs text-slate-500 py-4">Loading enrollment forecast...</p>
  }

  const { meta, model_metrics } = data
  return (
    <Card data-testid="forecast-panel">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
            <LineChart className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Enrollment Demand Forecast</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Forecasting {meta.target_semester_name} from {meta.observed_semester_ids.length}{' '}
              observed semesters
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {meta.is_synthetic && (
            <Badge variant="warning" data-testid="synthetic-badge">
              Synthetic history
            </Badge>
          )}
          <Badge variant="info" data-testid="champion-badge">
            Champion: {meta.champion_model}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {meta.note && (
          <Alert variant="warning" data-testid="forecast-note">
            {meta.note}
          </Alert>
        )}
        <div className="max-w-sm">
          <Select
            label="Course"
            value={String(courseId)}
            onChange={(e) => setCourseId(Number(e.target.value))}
            options={data.courses.map((c) => ({
              value: c.course_id,
              label: courseLabel(c.course_code, c.course_name),
            }))}
            data-testid="forecast-course-select"
          />
        </div>

        <ForecastChart course={course} targetName={meta.target_semester_name} />

        <div className="text-xs text-slate-600 space-y-1" data-testid="forecast-summary">
          <p>
            <span className="font-semibold text-slate-800">
              Forecast for {meta.target_semester_name}: {course.forecast}
            </span>{' '}
            (80% interval {course.interval_80[0]} to {course.interval_80[1]}; 95% interval{' '}
            {course.interval_95[0]} to {course.interval_95[1]})
          </p>
          <p>
            Per model:{' '}
            {Object.entries(course.forecasts)
              .map(([m, v]) => `${m} ${v}`)
              .join(' | ')}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="model-metrics-table">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 pr-4">Model</th>
                <th className="py-2 pr-4">Backtest MAE</th>
                <th className="py-2 pr-4">sMAPE %</th>
                <th className="py-2 pr-4">Last-origin MAE</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(model_metrics).map(([name, m]) => (
                <tr key={name} className="border-b border-slate-100">
                  <td className="py-2 pr-4 font-medium text-slate-800">
                    {name}
                    {name === meta.champion_model && (
                      <Badge variant="success" className="ml-2">
                        champion
                      </Badge>
                    )}
                  </td>
                  <td className="py-2 pr-4">{m.mae}</td>
                  <td className="py-2 pr-4">{m.smape_pct}</td>
                  <td className="py-2 pr-4">{m.last_origin_mae}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-[11px] text-slate-500">
          {meta.methodology} Held-out coverage of the 80% interval:{' '}
          {meta.held_out_coverage_80 === null
            ? 'n/a'
            : `${Math.round(meta.held_out_coverage_80 * 100)}%`}{' '}
          (calibrated on {meta.interval_calibration_n} backtest residuals).
        </p>
      </CardContent>
    </Card>
  )
}

export default ForecastPanel
