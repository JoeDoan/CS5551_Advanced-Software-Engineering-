import React, { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, LineChart } from 'lucide-react'
import { Alert, Badge, Card, CardContent, CardHeader, CardTitle, Select } from '../ui'
import {
  CourseForecast,
  EmpiricalBenchmark,
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

const formatCoveragePct = (ratio: number): string => `${Number((ratio * 100).toFixed(1))}%`

export const ForecastChart: React.FC<{ course: CourseForecast; targetName: string }> = ({
  course,
  targetName,
}) => {
  const n = course.history.length
  const labelStep = n > 8 ? Math.ceil(n / 6) : 1
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
      {course.history.map((h, i) => {
        const showLabel = i === 0 || i === n - 1 || i % labelStep === 0
        return (
          <g key={h.semester_id}>
            <circle cx={x(i)} cy={y(h.enrolled)} r="3.5" fill="#1d4ed8" />
            {showLabel && (
              <text
                x={x(i)}
                y={n > 8 && i === n - 1 ? H - 25 : H - 14}
                textAnchor="middle"
                fontSize={n > 8 ? '9' : '10'}
                fill="#64748b"
              >
                {shortSemester(h.semester_name)}
              </text>
            )}
          </g>
        )
      })}
      <circle cx={x(n)} cy={y(course.forecast)} r="5" fill="#d97706" />
      <text
        x={x(n)}
        y={H - 14}
        textAnchor="middle"
        fontSize={n > 8 ? '9' : '10'}
        fill="#b45309"
        fontWeight="bold"
      >
        {shortSemester(targetName)}
      </text>
    </svg>
  )
}

export const ForecastPanel: React.FC = () => {
  const [data, setData] = useState<EnrollmentForecast | null>(null)
  const [benchmark, setBenchmark] = useState<EmpiricalBenchmark | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [courseId, setCourseId] = useState<number | null>(null)

  useEffect(() => {
    let active = true
    insightsService
      .getForecast()
      .then((d) => {
        if (!active) return
        setData(d)
        setCourseId(d.courses[0]?.course_id ?? null)
        if (!d.meta.is_synthetic && typeof insightsService.getEmpiricalBenchmark === 'function') {
          insightsService
            .getEmpiricalBenchmark()
            .then((bm) => {
              if (active) setBenchmark(bm ?? null)
            })
            .catch(() => {
              if (active) setBenchmark(null)
            })
        } else {
          setBenchmark(null)
        }
      })
      .catch((e) => {
        if (active) setError(errorMessage(e))
      })
    return () => {
      active = false
    }
  }, [])

  const course = useMemo(
    () => data?.courses.find((c) => c.course_id === courseId) ?? null,
    [data, courseId]
  )

  const selectedCourseBenchmark = useMemo(() => {
    if (!benchmark || !course) return null
    return (
      benchmark.course_comparisons.find(
        (c) => c.course_code.trim().toUpperCase() === course.course_code.trim().toUpperCase()
      ) ??
      benchmark.course_comparisons[0] ??
      null
    )
  }, [benchmark, course])

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
    <div className="space-y-6">
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
            {meta.is_synthetic ? (
              <Badge variant="warning" data-testid="synthetic-badge">
                Synthetic history
              </Badge>
            ) : (
              <Badge variant="success" data-testid="real-data-badge">
                UIUC FOIA Registrar (2016–2025)
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

      {!meta.is_synthetic && benchmark && (
        <Card data-testid="empirical-benchmark-card">
          <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-700">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <CardTitle>
                  {benchmark.heldout_semester_name} Held-Out Empirical Benchmark
                </CardTitle>
                <p className="text-xs text-slate-500 mt-0.5">
                  {benchmark.observed_semesters_count} observed FOIA terms -&gt; Held-out{' '}
                  {benchmark.heldout_semester_name} ({benchmark.evaluated_courses_count} evaluated
                  courses)
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="success">{benchmark.dataset_source}</Badge>
              <Badge variant="info">
                {benchmark.courses_with_2yr_habit_pref} with 2-yr habit ·{' '}
                {benchmark.courses_without_pref} no preference
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">
              <span className="font-semibold text-slate-900">Provenance:</span>{' '}
              {benchmark.observed_semesters_count} observed FOIA terms -&gt; Held-out{' '}
              {benchmark.heldout_semester_name} · {benchmark.courses_with_2yr_habit_pref} courses
              with 2-yr causal habit preference · {benchmark.courses_without_pref} courses with no
              preference ({benchmark.preference_provenance}).
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                className="p-4 rounded-xl border border-slate-200 bg-white space-y-3"
                data-testid="benchmark-stage1"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Stage 1: Demand Forecast Benchmark
                  </span>
                  <Badge variant="info">{benchmark.forecast_benchmark.champion_model}</Badge>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200">
                    <div className="text-[11px] text-emerald-800">Champion MAE</div>
                    <div className="text-base font-extrabold text-emerald-900 mt-0.5">
                      {benchmark.forecast_benchmark.champion_mae}
                    </div>
                    <div className="text-[11px] text-emerald-700">
                      sMAPE {benchmark.forecast_benchmark.champion_smape_pct}%
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[11px] text-slate-500">Copy Fall 2025 Naive MAE</div>
                    <div className="text-base font-extrabold text-slate-800 mt-0.5">
                      {benchmark.forecast_benchmark.last_term_copy_naive_mae}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      sMAPE {benchmark.forecast_benchmark.last_term_copy_naive_smape_pct}%
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-700 pt-1">
                  <div className="flex items-center justify-between">
                    <span>MAE Reduction vs Copy Fall 2025</span>
                    <span className="font-bold text-emerald-700">
                      {benchmark.forecast_benchmark.mae_reduction_vs_last_term_pct}% reduction
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>80% Conformal Coverage</span>
                    <span className="font-semibold text-slate-900">
                      {formatCoveragePct(benchmark.forecast_benchmark.empirical_coverage_80)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>95% Conformal Coverage</span>
                    <span className="font-semibold text-slate-900">
                      {formatCoveragePct(benchmark.forecast_benchmark.empirical_coverage_95)}
                    </span>
                  </div>
                </div>
              </div>

              <div
                className="p-4 rounded-xl border border-slate-200 bg-white space-y-3"
                data-testid="benchmark-stage2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Stage 2: Predict-Then-Optimize Schedule vs UIUC Actual{' '}
                    {benchmark.heldout_semester_name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="success">
                      {benchmark.schedule_benchmark.hard_conflicts} Hard Conflicts
                    </Badge>
                    <Badge variant="neutral">{benchmark.schedule_benchmark.solver_status}</Badge>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-700">
                  <div className="flex items-center justify-between py-1 border-b border-slate-100">
                    <span>Room Overflows (Conformal-80 / Point / Copy-Last-Term)</span>
                    <span className="font-bold text-slate-900">
                      <span className="text-emerald-700">
                        {benchmark.schedule_benchmark.overflow_courses_conformal_80_sizing}
                      </span>{' '}
                      / {benchmark.schedule_benchmark.overflow_courses_point_forecast_sizing} /{' '}
                      {benchmark.schedule_benchmark.overflow_courses_last_term_sizing}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-slate-100">
                    <span>Seat Utilization (OptiSched vs UIUC Actual)</span>
                    <span className="font-semibold text-slate-900">
                      <span className="text-emerald-700">
                        {benchmark.schedule_benchmark.optisched_seat_utilization_pct}%
                      </span>{' '}
                      vs {benchmark.schedule_benchmark.uiuc_actual_seat_utilization_pct}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-slate-100">
                    <span>Empty-Seat Waste (OptiSched vs UIUC Actual)</span>
                    <span className="font-semibold text-slate-900">
                      <span className="text-emerald-700">
                        {benchmark.schedule_benchmark.optisched_empty_seat_waste_pct}%
                      </span>{' '}
                      vs {benchmark.schedule_benchmark.uiuc_empty_seat_waste_pct}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-slate-100">
                    <span>Midday 10am–2pm Concentration (OptiSched vs UIUC Actual)</span>
                    <span className="font-semibold text-slate-900">
                      <span className="text-emerald-700">
                        {benchmark.schedule_benchmark.optisched_midday_concentration_pct}%
                      </span>{' '}
                      vs {benchmark.schedule_benchmark.uiuc_midday_concentration_pct}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <span>2-Year Habit Continuity (preference courses)</span>
                    <span className="font-bold text-emerald-700">
                      {benchmark.schedule_benchmark.habit_continuity_on_pref_courses_pct}%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {selectedCourseBenchmark && (
              <div
                className="p-4 rounded-xl border border-blue-200 bg-blue-50/40 space-y-2.5 text-xs"
                data-testid="benchmark-selected-course"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-bold text-slate-900">
                    Held-Out {benchmark.heldout_semester_name} Audit:{' '}
                    {courseLabel(
                      selectedCourseBenchmark.course_code,
                      selectedCourseBenchmark.course_name
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge
                      variant={selectedCourseBenchmark.has_2yr_preference ? 'info' : 'neutral'}
                    >
                      {selectedCourseBenchmark.has_2yr_preference
                        ? '2-yr habit preference'
                        : 'No 2-yr preference'}
                    </Badge>
                    <Badge variant={selectedCourseBenchmark.within_80 ? 'success' : 'warning'}>
                      {selectedCourseBenchmark.within_80 ? 'Within 80% PI' : 'Outside 80% PI'}
                    </Badge>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-slate-700">
                  <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                    <div className="text-[11px] text-slate-500">Demand vs FOIA Ground Truth</div>
                    <div className="mt-0.5 font-medium text-slate-900">
                      Fall 2025: {selectedCourseBenchmark.fall_2025_enrolled} -&gt; Predicted:{' '}
                      {selectedCourseBenchmark.predicted_enrollment} [80% PI:{' '}
                      {selectedCourseBenchmark.interval_80[0]}–
                      {selectedCourseBenchmark.interval_80[1]}]
                    </div>
                    <div className="text-[11px] text-emerald-700 font-semibold mt-0.5">
                      Actual {benchmark.heldout_semester_name} FOIA:{' '}
                      {selectedCourseBenchmark.actual_enrollment} (|err|{' '}
                      {selectedCourseBenchmark.abs_error})
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                    <div className="text-[11px] text-slate-500">OptiSched Room &amp; Slot</div>
                    <div className="mt-0.5 font-semibold text-slate-900">
                      {selectedCourseBenchmark.optisched_room} (Cap{' '}
                      {selectedCourseBenchmark.optisched_room_capacity})
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5">
                      {selectedCourseBenchmark.optisched_slot}
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                    <div className="text-[11px] text-slate-500">UIUC Actual Room &amp; Slot</div>
                    <div className="mt-0.5 font-semibold text-slate-900">
                      {selectedCourseBenchmark.uiuc_actual_room} (Cap{' '}
                      {selectedCourseBenchmark.uiuc_actual_room_capacity})
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5">
                      {selectedCourseBenchmark.uiuc_actual_slot}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default ForecastPanel
