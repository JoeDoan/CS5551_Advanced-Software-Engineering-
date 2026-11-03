import React, { useEffect, useState } from 'react'
import { Alert, Badge, Button } from '../ui'
import {
  CoverageStrategy,
  DEFAULT_SCENARIO,
  ScenarioResponse,
  errorMessage,
  insightsService,
} from '../../services/insightsService'
import { AuthRole } from '../../types/api'

const TIME_LIMIT_SECONDS = 8

export interface BuyoutSummary {
  feasible: boolean
  headline: string
  detail: string[]
}

// The badge is built from the solver's own numbers only.
export const summarizeBuyout = (res: ScenarioResponse): BuyoutSummary => {
  const status = res.scenario.status
  if (status !== 'OPTIMAL' && status !== 'FEASIBLE') {
    return {
      feasible: false,
      headline: 'Not feasible as asked',
      detail: res.scenario.diagnosis.length ? res.scenario.diagnosis : [`Solver status: ${status}.`],
    }
  }
  const moved = res.diff.changed_courses.length
  const covered = res.diff.adjunct_sections.length
    ? `covered by an adjunct (${res.diff.adjunct_sections.join(', ')})`
    : res.diff.absorbers.length
      ? `covered by ${res.diff.absorbers.join(', ')}`
      : 'no coverage needed'
  const delta = res.diff.satisfaction_delta_pct
  const detail = [
    `${moved} course${moved === 1 ? '' : 's'} move; ${covered}.`,
    delta === null
      ? 'Satisfaction change not available.'
      : `Average instructor satisfaction changes by ${delta >= 0 ? '+' : ''}${delta.toFixed(1)} points.`,
    `Solver: ${status === 'OPTIMAL' ? 'proven optimal' : 'best found in the time limit'} for ${res.semester_name}.`,
  ]
  return { feasible: true, headline: 'Feasible', detail }
}

export interface BuyoutImpactProps {
  role: AuthRole
  userName: string
}

export const BuyoutImpact: React.FC<BuyoutImpactProps> = ({ role, userName }) => {
  const isCoordinator = role === 'coordinator'
  const [names, setNames] = useState<string[]>([])
  const [instructor, setInstructor] = useState(isCoordinator ? '' : userName)
  const [coverage, setCoverage] = useState<CoverageStrategy>('adjunct')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<BuyoutSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isCoordinator) return
    insightsService
      .getInstructorNames()
      .then((n) => {
        setNames(n)
        setInstructor((current) => current || n[0] || '')
      })
      .catch(() => setNames([]))
  }, [isCoordinator])

  const run = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await insightsService.simulate({
        ...DEFAULT_SCENARIO,
        buyouts: [{ instructor, max_courses: 1, reason: 'Commercialization effort' }],
        coverage_strategy: coverage,
        time_limit_seconds: TIME_LIMIT_SECONDS,
      })
      setResult(summarizeBuyout(res))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50/40 p-3 space-y-3" data-testid="buyout-card">
      <p className="text-sm font-semibold text-slate-800">What would a one-course release do to the schedule?</p>
      <p className="text-xs text-slate-600">
        This is a dry run on the department schedule. Nothing is saved or changed.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs text-slate-600">
          Instructor
          {isCoordinator ? (
            <select
              className="block mt-1 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              value={instructor}
              onChange={(e) => setInstructor(e.target.value)}
              data-testid="buyout-instructor"
            >
              {names.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          ) : (
            <span className="block mt-1 text-sm font-medium text-slate-800" data-testid="buyout-instructor">
              {instructor || 'Unknown'}
            </span>
          )}
        </label>
        <label className="text-xs text-slate-600">
          Who covers the course
          <select
            className="block mt-1 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            value={coverage}
            onChange={(e) => setCoverage(e.target.value as CoverageStrategy)}
            data-testid="buyout-coverage"
          >
            <option value="adjunct">An adjunct</option>
            <option value="overload">A colleague</option>
            <option value="none">Nobody</option>
          </select>
        </label>
        <Button onClick={run} disabled={busy || !instructor} data-testid="buyout-run">
          {busy ? 'Solving…' : 'Simulate course buyout impact'}
        </Button>
      </div>
      {error && <Alert variant="danger">{error}</Alert>}
      {result && (
        <div data-testid="buyout-result" className="space-y-1">
          <Badge variant={result.feasible ? 'success' : 'danger'}>{result.headline}</Badge>
          <ul className="list-disc pl-4 text-sm text-slate-700">
            {result.detail.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
