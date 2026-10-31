import React from 'react'
import { Alert, Badge } from '../ui'
import { ScenarioMetrics, ScenarioResponse } from '../../services/insightsService'

const fmt = (v: number | null | undefined, suffix = ''): string =>
  v === null || v === undefined ? 'n/a' : `${v}${suffix}`

const fmtDelta = (v: number | null | undefined, suffix = ''): string => {
  if (v === null || v === undefined) return ''
  const sign = v > 0 ? '+' : ''
  return `${sign}${v}${suffix}`
}

const statusVariant = (s: string): 'success' | 'warning' | 'danger' =>
  s === 'OPTIMAL' ? 'success' : s === 'FEASIBLE' ? 'warning' : 'danger'

export interface ScenarioResultViewProps {
  result: ScenarioResponse
  explanation?: string[]
  testId?: string
}

export const ScenarioResultView: React.FC<ScenarioResultViewProps> = ({
  result,
  explanation,
  testId = 'whatif-result',
}) => {
  const metricRow = (
    label: string,
    pick: (m: ScenarioMetrics) => string,
    delta: string,
    rowId: string
  ) => (
    <tr className="border-b border-slate-100" data-testid={rowId} key={label}>
      <td className="py-2 pr-4 text-slate-600">{label}</td>
      <td className="py-2 pr-4">{pick(result.baseline)}</td>
      <td className="py-2 pr-4">{pick(result.scenario)}</td>
      <td className="py-2 font-medium text-slate-800">{delta}</td>
    </tr>
  )

  return (
          <div className="space-y-4" data-testid={testId}>
      {explanation && explanation.length > 0 && (
        <div
          className="rounded-xl border border-blue-200 bg-blue-50/60 p-3 text-xs text-slate-800"
          data-testid="explanation"
        >
          <div className="font-semibold text-blue-800 mb-1">What this means</div>
          <ul className="list-disc ml-4 space-y-1">
            {explanation.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] text-slate-500">
            Written from the solver's own numbers, not by a language model.
          </p>
        </div>
      )}
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
  )
}

export default ScenarioResultView
