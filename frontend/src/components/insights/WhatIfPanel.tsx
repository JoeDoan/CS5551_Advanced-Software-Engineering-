import React, { useEffect, useState } from 'react'
import { FlaskConical, Plus, Trash2 } from 'lucide-react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Input, Select } from '../ui'
import {
  ChangePolicy,
  CoverageStrategy,
  DEFAULT_SCENARIO,
  ScenarioMetrics,
  ScenarioResponse,
  ScenarioSpec,
  errorMessage,
  insightsService,
} from '../../services/insightsService'
import { AuthRole } from '../../types/api'

export const DEPARTMENTS = ['CS', 'MATH', 'ECE', 'PHYS', 'BIOL', 'CHEM', 'STAT']

const STRATEGY_HELP: Record<CoverageStrategy, string> = {
  none: 'No replacement. With zero slack in instructor capacity this is provably infeasible.',
  overload:
    'A qualified colleague in the same subject area may take one extra course. The solver picks who.',
  adjunct: 'A synthetic adjunct covers the freed section. No colleague is overloaded.',
}

export interface WhatIfPanelProps {
  role: AuthRole
  userName: string
}

const fmt = (v: number | null | undefined, suffix = ''): string =>
  v === null || v === undefined ? 'n/a' : `${v}${suffix}`

const fmtDelta = (v: number | null | undefined, suffix = ''): string => {
  if (v === null || v === undefined) return ''
  const sign = v > 0 ? '+' : ''
  return `${sign}${v}${suffix}`
}

const statusVariant = (s: string): 'success' | 'warning' | 'danger' =>
  s === 'OPTIMAL' ? 'success' : s === 'FEASIBLE' ? 'warning' : 'danger'

export const WhatIfPanel: React.FC<WhatIfPanelProps> = ({ role, userName }) => {
  const isCoordinator = role === 'coordinator'
  const [useForecast, setUseForecast] = useState(false)
  const [growth, setGrowth] = useState<{ department: string; pct: number }[]>([])
  const [scale, setScale] = useState(1)
  const [buyoutOn, setBuyoutOn] = useState(false)
  const [instructors, setInstructors] = useState<string[]>([])
  const [instructor, setInstructor] = useState(isCoordinator ? '' : userName)
  const [strategy, setStrategy] = useState<CoverageStrategy>('overload')
  const [reason, setReason] = useState('')
  const [timeLimit, setTimeLimit] = useState(DEFAULT_SCENARIO.time_limit_seconds)
  const [policy, setPolicy] = useState<ChangePolicy>(DEFAULT_SCENARIO.change_policy)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScenarioResponse | null>(null)

  useEffect(() => {
    if (!isCoordinator) return
    insightsService
      .getInstructorNames()
      .then((names) => {
        setInstructors(names)
        setInstructor((cur) => cur || names[0] || '')
      })
      .catch((e) => setError(errorMessage(e)))
  }, [isCoordinator])

  const run = async () => {
    const spec: ScenarioSpec = {
      ...DEFAULT_SCENARIO,
      use_forecast: isCoordinator && useForecast,
      enrollment_growth: isCoordinator ? growth.filter((g) => g.pct !== 0) : [],
      room_capacity_scale: isCoordinator ? scale : 1,
      coverage_strategy: strategy,
      time_limit_seconds: timeLimit,
      change_policy: policy,
      buyouts:
        buyoutOn && instructor
          ? [{ instructor, max_courses: 1, reason: reason.trim() || undefined }]
          : [],
    }
    setRunning(true)
    setError(null)
    try {
      setResult(await insightsService.simulate(spec))
    } catch (e) {
      setResult(null)
      setError(errorMessage(e))
    } finally {
      setRunning(false)
    }
  }

  const metricRow = (
    label: string,
    pick: (m: ScenarioMetrics) => string,
    delta: string,
    testId: string
  ) => (
    <tr className="border-b border-slate-100" data-testid={testId} key={label}>
      <td className="py-2 pr-4 text-slate-600">{label}</td>
      <td className="py-2 pr-4">{result && pick(result.baseline)}</td>
      <td className="py-2 pr-4">{result && pick(result.scenario)}</td>
      <td className="py-2 font-medium text-slate-800">{delta}</td>
    </tr>
  )

  return (
    <Card data-testid="whatif-panel">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-violet-50 text-violet-600">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>What-If Simulator</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Re-solves Spring 2027 with CP-SAT as a dry run. Nothing is saved.
            </p>
          </div>
        </div>
        <Badge variant="info">{isCoordinator ? 'Coordinator' : 'Faculty: own buyout only'}</Badge>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid md:grid-cols-2 gap-5">
          {isCoordinator && (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={useForecast}
                  onChange={(e) => setUseForecast(e.target.checked)}
                  data-testid="use-forecast"
                />
                Use forecast enrollment instead of the current plan
              </label>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-700">Enrollment growth</span>
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={<Plus className="w-3 h-3" />}
                    onClick={() => setGrowth([...growth, { department: 'CS', pct: 10 }])}
                    disabled={growth.length >= 3}
                    data-testid="add-growth"
                  >
                    Add
                  </Button>
                </div>
                {growth.map((g, idx) => (
                  <div key={idx} className="flex items-end gap-2" data-testid="growth-row">
                    <Select
                      aria-label="Department"
                      value={g.department}
                      onChange={(e) =>
                        setGrowth(
                          growth.map((x, i) =>
                            i === idx ? { ...x, department: e.target.value } : x
                          )
                        )
                      }
                      options={DEPARTMENTS.map((d) => ({ value: d, label: d }))}
                    />
                    <Input
                      aria-label="Growth percent"
                      type="number"
                      min={-50}
                      max={100}
                      value={g.pct}
                      onChange={(e) =>
                        setGrowth(
                          growth.map((x, i) =>
                            i === idx ? { ...x, pct: Number(e.target.value) } : x
                          )
                        )
                      }
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label="Remove growth row"
                      onClick={() => setGrowth(growth.filter((_, i) => i !== idx))}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <Select
                label="Room capacity scale"
                value={String(scale)}
                onChange={(e) => setScale(Number(e.target.value))}
                options={[0.8, 0.9, 1, 1.1, 1.2].map((v) => ({ value: v, label: `${v}x` }))}
                data-testid="capacity-scale"
              />
            </div>
          )}

          <div className="space-y-3">
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={buyoutOn}
                onChange={(e) => setBuyoutOn(e.target.checked)}
                data-testid="buyout-toggle"
              />
              Simulate a one-course commercialization / grant buyout
            </label>
            {buyoutOn && (
              <div className="space-y-3">
                {isCoordinator ? (
                  <Select
                    label="Instructor"
                    value={instructor}
                    onChange={(e) => setInstructor(e.target.value)}
                    options={instructors.map((n) => ({ value: n, label: n }))}
                    data-testid="buyout-instructor"
                  />
                ) : (
                  <p className="text-xs text-slate-700" data-testid="buyout-self">
                    Instructor: <span className="font-semibold">{userName}</span>
                  </p>
                )}
                <Select
                  label="Coverage strategy"
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value as CoverageStrategy)}
                  options={[
                    { value: 'overload', label: 'Colleague overload' },
                    { value: 'adjunct', label: 'Adjunct replacement' },
                    { value: 'none', label: 'No replacement' },
                  ]}
                  data-testid="coverage-strategy"
                />
                <p className="text-[11px] text-slate-500">{STRATEGY_HELP[strategy]}</p>
                <Input
                  label="Reason (optional)"
                  value={reason}
                  maxLength={120}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g. NSF I-Corps award"
                />
              </div>
            )}
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4 max-w-2xl">
          <Select
            label="Schedule changes"
            value={policy}
            onChange={(e) => setPolicy(e.target.value as ChangePolicy)}
            options={[
              { value: 'minimal', label: 'Keep everything else (minimal)' },
              { value: 'reoptimize', label: 'Re-optimize the whole timetable' },
            ]}
            helperText="Minimal moves only what the scenario forces. Re-optimize may move many unrelated courses."
            data-testid="change-policy"
          />
          <Select
            label="Solver time limit"
            value={String(timeLimit)}
            onChange={(e) => setTimeLimit(Number(e.target.value))}
            options={[
              { value: 10, label: '10 s (quick)' },
              { value: 20, label: '20 s (default)' },
              { value: 30, label: '30 s (tightest)' },
            ]}
            helperText="Longer limits let CP-SAT prove the answer closer to optimal."
            data-testid="time-limit"
          />
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={run} isLoading={running} data-testid="run-scenario">
            Run simulation
          </Button>
          {running && (
            <span className="text-xs text-slate-500">
              Solving. The first run also solves the baseline and can take up to a minute.
            </span>
          )}
        </div>

        {error && (
          <Alert variant="danger" title="Simulation failed" data-testid="whatif-error">
            {error}
          </Alert>
        )}

        {result && (
          <div className="space-y-4" data-testid="whatif-result">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span>Baseline</span>
              <Badge variant={statusVariant(result.baseline.status)} data-testid="baseline-status">
                {result.baseline.status}
              </Badge>
              <span>Scenario</span>
              <Badge variant={statusVariant(result.scenario.status)} data-testid="scenario-status">
                {result.scenario.status}
              </Badge>
            </div>

            {result.scenario.diagnosis.length > 0 && (
              <Alert variant="danger" title="Why this is infeasible" data-testid="diagnosis">
                <ul className="list-disc ml-4 space-y-1">
                  {result.scenario.diagnosis.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </Alert>
            )}

            {result.scenario.diagnosis.length === 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs" data-testid="metrics-table">
                  <thead>
                    <tr className="text-left text-slate-500 border-b border-slate-200">
                      <th className="py-2 pr-4">Metric</th>
                      <th className="py-2 pr-4">Baseline</th>
                      <th className="py-2 pr-4">Scenario</th>
                      <th className="py-2">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metricRow(
                      'Average satisfaction',
                      (m) => fmt(m.avg_satisfaction_pct, '%'),
                      fmtDelta(result.diff.satisfaction_delta_pct, ' pts'),
                      'row-satisfaction'
                    )}
                    {metricRow(
                      'Minimum satisfaction',
                      (m) => fmt(m.min_satisfaction_pct, '%'),
                      '',
                      'row-min-satisfaction'
                    )}
                    {metricRow(
                      'Satisfaction Gini',
                      (m) => fmt(m.satisfaction_gini),
                      fmtDelta(result.diff.satisfaction_gini_delta),
                      'row-gini'
                    )}
                    {metricRow(
                      'Workload Gini',
                      (m) => fmt(m.workload_gini),
                      fmtDelta(result.diff.workload_gini_delta),
                      'row-workload'
                    )}
                    {metricRow(
                      'Room-slot utilization',
                      (m) => fmt(m.slot_utilization_pct, '%'),
                      fmtDelta(result.diff.slot_utilization_delta_pct, ' pts'),
                      'row-utilization'
                    )}
                    {metricRow(
                      'Seat occupancy',
                      (m) => fmt(m.seat_occupancy_pct, '%'),
                      fmtDelta(result.diff.seat_occupancy_delta_pct, ' pts'),
                      'row-occupancy'
                    )}
                    {metricRow(
                      'Proven gap to optimal (lower is better)',
                      (m) => fmt(m.optimality_gap_pct, '%'),
                      '',
                      'row-gap'
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {result.scenario.status === 'FEASIBLE' && (
              <p className="text-[11px] text-amber-700" data-testid="gap-note">
                The scenario was not proven optimal within the time limit (gap{' '}
                {fmt(result.scenario.optimality_gap_pct, '%')}). Rerun with a longer limit to
                tighten the comparison.
              </p>
            )}

            {(result.diff.released.length > 0 ||
              result.diff.absorbers.length > 0 ||
              result.diff.adjunct_sections.length > 0) && (
              <ul className="text-xs text-slate-700 space-y-1" data-testid="coverage-summary">
                {result.diff.released.length > 0 && (
                  <li>Released: {result.diff.released.join(', ')}</li>
                )}
                {result.diff.absorbers.length > 0 && (
                  <li>Absorbed by: {result.diff.absorbers.join(', ')}</li>
                )}
                {result.diff.adjunct_sections.length > 0 && (
                  <li>Adjunct sections: {result.diff.adjunct_sections.join(', ')}</li>
                )}
              </ul>
            )}

            {result.diff.changed_courses.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-800 mb-2">
                  Courses that moved ({result.diff.changed_courses.length})
                </h3>
                <ul className="space-y-1 text-xs text-slate-700" data-testid="changed-courses">
                  {result.diff.changed_courses.map((c) => (
                    <li key={c.course}>
                      <span className="font-semibold">{c.course}</span>:{' '}
                      {c.instructors_before.join(' + ')} in {c.room_before} (slot {c.slot_before})
                      {' to '}
                      {c.instructors_after.join(' + ')} in {c.room_after} (slot {c.slot_after})
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <ul className="text-[11px] text-slate-500 space-y-1" data-testid="scenario-notes">
              {result.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default WhatIfPanel
