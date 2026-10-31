import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AskOptiSched, specChips } from '../AskOptiSched'
import { InsightsPage } from '../../../pages/InsightsPage'
import {
  AskResult,
  CopilotStatus,
  DEFAULT_SCENARIO,
  ParseResult,
  ScenarioMetrics,
  ScenarioResponse,
  ScenarioSpec,
  copilotService,
  insightsService,
} from '../../../services/insightsService'

const LEE = 'Dr. Yugyung Lee'

const status = (over: Partial<CopilotStatus> = {}): CopilotStatus => ({
  llm_enabled: false,
  model: null,
  note: '',
  ...over,
})

const spec = (over: Partial<ScenarioSpec> = {}): ScenarioSpec => ({ ...DEFAULT_SCENARIO, ...over })

const parseResult = (over: Partial<ParseResult> = {}): ParseResult => ({
  prompt: 'p',
  parser_used: 'rules',
  llm_status: 'not_configured',
  spec: spec({
    enrollment_growth: [{ department: 'CS', pct: 20 }],
    buyouts: [{ instructor: LEE, max_courses: 1 }],
    coverage_strategy: 'adjunct',
  }),
  warnings: [],
  understood: true,
  rules_agree: null,
  ...over,
})

const metrics = (over: Partial<ScenarioMetrics> = {}): ScenarioMetrics => ({
  status: 'OPTIMAL',
  wall_time_seconds: 10,
  optimality_gap_pct: 0,
  scheduled_courses: 40,
  avg_satisfaction_pct: 97,
  min_satisfaction_pct: 80,
  satisfaction_gini: 0.02,
  workload_gini: 0,
  slot_utilization_pct: 22.2,
  seat_occupancy_pct: 55,
  rooms_used: 11,
  instructor_loads: {},
  diagnosis: [],
  ...over,
})

const askResult = (): AskResult => {
  const result: ScenarioResponse = {
    spec: spec(),
    semester_name: 'Spring 2027',
    baseline: metrics(),
    scenario: metrics(),
    diff: {
      status_before: 'OPTIMAL',
      status_after: 'OPTIMAL',
      satisfaction_delta_pct: 0,
      satisfaction_gini_delta: 0,
      workload_gini_delta: 0,
      slot_utilization_delta_pct: 0,
      seat_occupancy_delta_pct: 0,
      changed_courses: [],
      absorbers: [],
      released: [LEE],
      adjunct_sections: ['CS 101 Intro to CS'],
    },
    notes: ['Dry run: nothing was saved.'],
  }
  return {
    parse: null,
    result,
    explanation: [`${LEE} is limited to 1 course(s) in Spring 2027.`, 'An adjunct covers: CS 101 Intro to CS.'],
  }
}

const mockStatus = (s = status()) => vi.spyOn(copilotService, 'getStatus').mockResolvedValue(s)

const interpret = async (text = 'CS grows 20% and Dr. Lee takes a buyout') => {
  fireEvent.change(screen.getByTestId('ask-prompt'), { target: { value: text } })
  fireEvent.click(screen.getByTestId('ask-interpret'))
  await screen.findByTestId('ask-parsed')
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('specChips', () => {
  it('describes every part of a spec and can remove each one', () => {
    const full = spec({
      use_forecast: true,
      enrollment_growth: [{ department: 'BIOL', pct: -15 }],
      buyouts: [{ instructor: LEE, max_courses: 1 }],
      coverage_strategy: 'none',
      room_capacity_scale: 0.9,
      blocked_room_slots: [{ room_number: 'SCB 205', slot_id: 3 }],
      change_policy: 'reoptimize',
    })
    const chips = specChips(full)
    expect(chips.map((c) => c.label)).toEqual([
      'Use forecast enrollment',
      'BIOL enrollment -15%',
      `${LEE}: buyout to 1 course (nobody covers)`,
      'Room capacity x0.9',
      'Reserve SCB 205 at slot 3',
      'Re-optimize the whole timetable',
    ])
    const emptied = chips.reduce((s, c) => c.remove(s), full)
    expect(specChips(emptied)).toEqual([])
  })

  it('shows nothing for an unchanged spec', () => {
    expect(specChips(spec())).toEqual([])
  })
})

describe('AskOptiSched', () => {
  it('shows whether Claude is on and fills the prompt from an example', async () => {
    mockStatus(status({ llm_enabled: true, model: 'claude-opus-5-5' }))
    render(<AskOptiSched role="coordinator" />)
    expect(await screen.findByTestId('llm-status')).toHaveTextContent('Claude on (claude-opus-5-5)')
    expect(screen.getByTestId('ask-use-llm')).toBeChecked()
    expect(screen.getByTestId('ask-interpret')).toBeDisabled()
    fireEvent.click(screen.getAllByTestId('ask-example')[0])
    expect(screen.getByTestId('ask-prompt')).toHaveValue(
      'What if CS enrollment grows 20% and Dr. Lee takes a 1-course buyout?'
    )
    expect(screen.getByTestId('ask-interpret')).not.toBeDisabled()
  })

  it('hides the Claude checkbox when Claude is not configured', async () => {
    mockStatus()
    render(<AskOptiSched role="coordinator" />)
    expect(await screen.findByTestId('llm-status')).toHaveTextContent('Rule-based (Claude off)')
    expect(screen.queryByTestId('ask-use-llm')).not.toBeInTheDocument()
  })

  it('interprets a prompt into removable chips and runs exactly what is left', async () => {
    mockStatus()
    const parse = vi.spyOn(copilotService, 'parse').mockResolvedValue(
      parseResult({ warnings: ['No department named for the 7% change; applied to all departments.'] })
    )
    const ask = vi.spyOn(copilotService, 'ask').mockResolvedValue(askResult())
    render(<AskOptiSched role="coordinator" />)
    await interpret()

    expect(parse).toHaveBeenCalledWith('CS grows 20% and Dr. Lee takes a buyout', true)
    expect(screen.getByTestId('parser-badge')).toHaveTextContent('Rule-based parser')
    expect(screen.getByTestId('ask-warnings')).toHaveTextContent('applied to all departments')
    const chips = screen.getAllByTestId('ask-chip')
    expect(chips).toHaveLength(2)
    expect(chips[0]).toHaveTextContent('CS enrollment +20%')

    fireEvent.click(within(chips[0]).getByRole('button'))
    expect(screen.getAllByTestId('ask-chip')).toHaveLength(1)

    fireEvent.click(screen.getByTestId('ask-run'))
    expect(await screen.findByTestId('ask-result')).toBeInTheDocument()
    const sent = ask.mock.calls[0][0]
    expect(sent.enrollment_growth).toEqual([])
    expect(sent.buyouts).toEqual([{ instructor: LEE, max_courses: 1 }])
    expect(sent.coverage_strategy).toBe('adjunct')
    expect(sent.time_limit_seconds).toBe(20)
    expect(screen.getByTestId('explanation')).toHaveTextContent('An adjunct covers: CS 101 Intro to CS.')
    expect(screen.getByTestId('explanation')).toHaveTextContent(/not by a language model/i)
  })

  it('cannot run once every chip has been removed', async () => {
    mockStatus()
    vi.spyOn(copilotService, 'parse').mockResolvedValue(
      parseResult({ spec: spec({ room_capacity_scale: 0.9 }) })
    )
    render(<AskOptiSched role="coordinator" />)
    await interpret('rooms 10% smaller')
    fireEvent.click(within(screen.getByTestId('ask-chip')).getByRole('button'))
    expect(screen.getByTestId('ask-no-chips')).toBeInTheDocument()
    expect(screen.queryByTestId('ask-run')).not.toBeInTheDocument()
  })

  it('labels a Claude result and surfaces disagreement with the rule-based parser', async () => {
    mockStatus(status({ llm_enabled: true, model: 'claude-opus-5-5' }))
    vi.spyOn(copilotService, 'parse').mockResolvedValue(
      parseResult({ parser_used: 'llm', llm_status: 'ok', rules_agree: false })
    )
    render(<AskOptiSched role="coordinator" />)
    await interpret()
    expect(screen.getByTestId('parser-badge')).toHaveTextContent('Claude')
    expect(screen.getByTestId('rules-disagree')).toBeInTheDocument()
  })

  it('tells the user when Claude failed and the rules took over', async () => {
    mockStatus(status({ llm_enabled: true, model: 'claude-opus-5-5' }))
    vi.spyOn(copilotService, 'parse').mockResolvedValue(
      parseResult({ llm_status: 'failed: rate limited by the API; used the rule-based parser' })
    )
    render(<AskOptiSched role="coordinator" />)
    await interpret()
    expect(screen.getByTestId('llm-failed')).toHaveTextContent('rate limited by the API')
    expect(screen.getByTestId('parser-badge')).toHaveTextContent('Rule-based parser')
  })

  it('passes the Claude opt-out through to the API', async () => {
    mockStatus(status({ llm_enabled: true, model: 'claude-opus-5-5' }))
    const parse = vi.spyOn(copilotService, 'parse').mockResolvedValue(parseResult())
    render(<AskOptiSched role="coordinator" />)
    await screen.findByTestId('ask-use-llm')
    fireEvent.click(screen.getByTestId('ask-use-llm'))
    await interpret()
    expect(parse).toHaveBeenCalledWith(expect.any(String), false)
  })

  it('shows guidance and no Run button when nothing was understood', async () => {
    mockStatus()
    vi.spyOn(copilotService, 'parse').mockResolvedValue(
      parseResult({
        understood: false,
        spec: spec(),
        warnings: ['I could not find a scenario change in that request.'],
      })
    )
    render(<AskOptiSched role="coordinator" />)
    await interpret('tell me a joke')
    expect(screen.getByTestId('ask-warnings')).toHaveTextContent('could not find a scenario change')
    expect(screen.queryAllByTestId('ask-chip')).toHaveLength(0)
    expect(screen.queryByTestId('ask-run')).not.toBeInTheDocument()
  })

  it('shows API errors, such as faculty scope violations', async () => {
    mockStatus()
    vi.spyOn(copilotService, 'parse').mockRejectedValue(
      new Error('Faculty can only simulate their own course buyout.')
    )
    render(<AskOptiSched role="instructor" />)
    fireEvent.change(screen.getByTestId('ask-prompt'), { target: { value: 'What if CS grows 20%?' } })
    fireEvent.click(screen.getByTestId('ask-interpret'))
    expect(await screen.findByTestId('ask-error')).toHaveTextContent('own course buyout')
    expect(screen.queryByTestId('ask-parsed')).not.toBeInTheDocument()
  })

  it('offers first-person examples to faculty', async () => {
    mockStatus()
    render(<AskOptiSched role="instructor" />)
    await screen.findByTestId('llm-status')
    expect(screen.getAllByTestId('ask-example')[0]).toHaveTextContent('I want a course buyout')
  })
})

describe('InsightsPage', () => {
  it('has an Ask OptiSched tab', async () => {
    mockStatus()
    vi.spyOn(insightsService, 'getForecast').mockRejectedValue(new Error('offline'))
    render(<InsightsPage />)
    fireEvent.click(screen.getByTestId('tab-ask'))
    await waitFor(() => expect(screen.getByTestId('ask-panel')).toBeInTheDocument())
  })
})
