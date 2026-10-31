import React, { useEffect, useState } from 'react'
import { Sparkles, X } from 'lucide-react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  AskResult,
  CopilotStatus,
  ParseResult,
  ScenarioSpec,
  copilotService,
  errorMessage,
} from '../../services/insightsService'
import { AuthRole } from '../../types/api'
import { ScenarioResultView } from './ScenarioResultView'

const RUN_TIME_LIMIT_SECONDS = 20

const COORDINATOR_EXAMPLES = [
  'What if CS enrollment grows 20% and Dr. Lee takes a 1-course buyout?',
  'Biology drops 15% and the rooms are 10% smaller',
  'Dr. Rao gets a course release covered by an adjunct',
  'Use forecast enrollment and give Dr. Kilway a buyout, nobody covers it',
]
const FACULTY_EXAMPLES = [
  'I want a course buyout, covered by an adjunct',
  'What if I take a one-course release and a colleague covers it?',
]

export interface Chip {
  key: string
  label: string
  remove: (s: ScenarioSpec) => ScenarioSpec
}

export const specChips = (spec: ScenarioSpec): Chip[] => {
  const chips: Chip[] = []
  if (spec.use_forecast) {
    chips.push({ key: 'forecast', label: 'Use forecast enrollment', remove: (s) => ({ ...s, use_forecast: false }) })
  }
  spec.enrollment_growth.forEach((g) =>
    chips.push({
      key: `growth:${g.department}`,
      label: `${g.department} enrollment ${g.pct >= 0 ? '+' : ''}${g.pct}%`,
      remove: (s) => ({ ...s, enrollment_growth: s.enrollment_growth.filter((x) => x.department !== g.department) }),
    })
  )
  spec.buyouts.forEach((b) =>
    chips.push({
      key: `buyout:${b.instructor}`,
      label: `${b.instructor}: buyout to ${b.max_courses} course (${
        { overload: 'a colleague covers', adjunct: 'an adjunct covers', none: 'nobody covers' }[spec.coverage_strategy]
      })`,
      remove: (s) => ({ ...s, buyouts: s.buyouts.filter((x) => x.instructor !== b.instructor) }),
    })
  )
  if (spec.room_capacity_scale !== 1) {
    chips.push({
      key: 'capacity',
      label: `Room capacity x${spec.room_capacity_scale}`,
      remove: (s) => ({ ...s, room_capacity_scale: 1 }),
    })
  }
  spec.blocked_room_slots.forEach((b) =>
    chips.push({
      key: `block:${b.room_number}:${b.slot_id}`,
      label: `Reserve ${b.room_number} at slot ${b.slot_id}`,
      remove: (s) => ({
        ...s,
        blocked_room_slots: s.blocked_room_slots.filter(
          (x) => !(x.room_number === b.room_number && x.slot_id === b.slot_id)
        ),
      }),
    })
  )
  if (spec.change_policy === 'reoptimize') {
    chips.push({
      key: 'policy',
      label: 'Re-optimize the whole timetable',
      remove: (s) => ({ ...s, change_policy: 'minimal' }),
    })
  }
  return chips
}

export interface AskOptiSchedProps {
  role: AuthRole
}

export const AskOptiSched: React.FC<AskOptiSchedProps> = ({ role }) => {
  const [status, setStatus] = useState<CopilotStatus | null>(null)
  const [prompt, setPrompt] = useState('')
  const [useLlm, setUseLlm] = useState(true)
  const [parsing, setParsing] = useState(false)
  const [running, setRunning] = useState(false)
  const [parsed, setParsed] = useState<ParseResult | null>(null)
  const [spec, setSpec] = useState<ScenarioSpec | null>(null)
  const [answer, setAnswer] = useState<AskResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    copilotService.getStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  const examples = role === 'coordinator' ? COORDINATOR_EXAMPLES : FACULTY_EXAMPLES

  const interpret = async () => {
    setParsing(true)
    setError(null)
    setAnswer(null)
    try {
      const res = await copilotService.parse(prompt.trim(), useLlm)
      setParsed(res)
      setSpec(res.understood ? res.spec : null)
    } catch (e) {
      setParsed(null)
      setSpec(null)
      setError(errorMessage(e))
    } finally {
      setParsing(false)
    }
  }

  const run = async () => {
    if (!spec) return
    setRunning(true)
    setError(null)
    try {
      setAnswer(await copilotService.ask({ ...spec, time_limit_seconds: RUN_TIME_LIMIT_SECONDS }))
    } catch (e) {
      setAnswer(null)
      setError(errorMessage(e))
    } finally {
      setRunning(false)
    }
  }

  const chips = spec ? specChips(spec) : []

  return (
    <Card data-testid="ask-panel">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Ask OptiSched</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Describe a scenario in plain English. You confirm what was understood, then the CP-SAT
              solver runs it. Nothing is saved.
            </p>
          </div>
        </div>
        {status && (
          <Badge variant={status.llm_enabled ? 'success' : 'neutral'} data-testid="llm-status">
            {status.llm_enabled ? `Claude on (${status.model})` : 'Rule-based (Claude off)'}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="e.g. What if CS enrollment grows 20% and Dr. Lee takes a 1-course buyout?"
          className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          data-testid="ask-prompt"
          aria-label="Scenario in plain English"
        />
        <div className="flex flex-wrap gap-2">
          {examples.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setPrompt(ex)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] text-slate-600 hover:bg-slate-100"
              data-testid="ask-example"
            >
              {ex}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <Button
            onClick={interpret}
            isLoading={parsing}
            disabled={prompt.trim().length < 3}
            data-testid="ask-interpret"
          >
            Interpret
          </Button>
          {status?.llm_enabled && (
            <label className="flex items-center gap-2 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                data-testid="ask-use-llm"
              />
              Use Claude to interpret
            </label>
          )}
        </div>

        {error && (
          <Alert variant="danger" title="Something went wrong" data-testid="ask-error">
            {error}
          </Alert>
        )}

        {parsed && (
          <div className="space-y-3" data-testid="ask-parsed">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
              <span>Interpreted by</span>
              <Badge variant={parsed.parser_used === 'llm' ? 'success' : 'neutral'} data-testid="parser-badge">
                {parsed.parser_used === 'llm' ? 'Claude' : 'Rule-based parser'}
              </Badge>
              {parsed.rules_agree === false && (
                <Badge variant="warning" data-testid="rules-disagree">
                  Rule-based parser read it differently
                </Badge>
              )}
            </div>
            {parsed.llm_status.startsWith('failed') && (
              <Alert variant="warning" data-testid="llm-failed">
                Claude was unavailable ({parsed.llm_status.replace('failed: ', '')}).
              </Alert>
            )}
            {parsed.warnings.length > 0 && (
              <Alert variant="warning" title="Check this" data-testid="ask-warnings">
                <ul className="list-disc ml-4 space-y-1">
                  {parsed.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </Alert>
            )}
            {chips.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1.5">
                  Understood as (remove anything that is wrong)
                </div>
                <div className="flex flex-wrap gap-2" data-testid="ask-chips">
                  {chips.map((chip) => (
                    <span
                      key={chip.key}
                      className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-900"
                      data-testid="ask-chip"
                    >
                      {chip.label}
                      <button
                        type="button"
                        aria-label={`Remove ${chip.label}`}
                        onClick={() => spec && setSpec(chip.remove(spec))}
                        className="rounded-full p-0.5 hover:bg-blue-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
            {spec && chips.length === 0 && (
              <p className="text-xs text-slate-500" data-testid="ask-no-chips">
                Everything was removed. Interpret a new request to continue.
              </p>
            )}
            {spec && chips.length > 0 && (
              <div className="flex items-center gap-3">
                <Button onClick={run} isLoading={running} data-testid="ask-run">
                  Run this scenario
                </Button>
                {running && (
                  <span className="text-xs text-slate-500">
                    Solving. The first run also solves the baseline and can take up to a minute.
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {answer && (
          <ScenarioResultView
            result={answer.result}
            explanation={answer.explanation}
            testId="ask-result"
          />
        )}
      </CardContent>
    </Card>
  )
}

export default AskOptiSched
