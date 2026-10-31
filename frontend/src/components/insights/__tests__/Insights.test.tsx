import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ForecastPanel, shortSemester } from '../ForecastPanel'
import { BottleneckBoard } from '../BottleneckBoard'
import { WhatIfPanel } from '../WhatIfPanel'
import { InsightsPage } from '../../../pages/InsightsPage'
import { FairnessAnalyticsPanel } from '../../admin/FairnessAnalyticsPanel'
import {
  BottleneckItem,
  BottleneckReport,
  EnrollmentForecast,
  ForecastMeta,
  ScenarioMetrics,
  ScenarioResponse,
  insightsService,
} from '../../../services/insightsService'

const meta: ForecastMeta = {
  target_semester_id: 6,
  target_semester_name: 'Spring 2027',
  observed_semester_ids: [1, 2, 3, 4, 5],
  backtest_origins: [4, 5],
  champion_model: 'damped_trend',
  interval_calibration_n: 80,
  held_out_coverage_80: 0.825,
  data_source: 'synthetic',
  is_synthetic: true,
  methodology: 'Rolling-origin backtest.',
  note: 'Enrollment history is SYNTHETIC (seeded generator, not registrar data).',
}

const history = (base: number) =>
  ['Fall 2024', 'Spring 2025', 'Fall 2025', 'Spring 2026', 'Fall 2026'].map((n, i) => ({
    semester_id: i + 1,
    semester_name: n,
    enrolled: base + i,
    waitlist: 2,
  }))

const forecast: EnrollmentForecast = {
  meta,
  model_metrics: {
    seasonal_naive: { mae: 3.8, smape_pct: 7.8, last_origin_mae: 4.3, last_origin_smape_pct: 8.4 },
    damped_trend: { mae: 3.2, smape_pct: 6.5, last_origin_mae: 3.5, last_origin_smape_pct: 6.3 },
    pooled_ridge: { mae: 4.4, smape_pct: 8.4, last_origin_mae: 2.0, last_origin_smape_pct: 3.7 },
  },
  skipped_course_ids: [],
  courses: [
    {
      course_id: 1,
      course_code: 'CS 101',
      course_name: 'Intro to CS',
      department: 'CS',
      history: history(90),
      forecasts: { seasonal_naive: 83, damped_trend: 98, pooled_ridge: 94.6 },
      forecast: 98,
      interval_80: [87.8, 108.2],
      interval_95: [81.6, 114.4],
    },
    {
      course_id: 2,
      course_code: 'MATH 110',
      course_name: 'College Algebra',
      department: 'MATH',
      history: history(60),
      forecasts: { seasonal_naive: 60, damped_trend: 61, pooled_ridge: 62 },
      forecast: 61,
      interval_80: [55, 67],
      interval_95: [50, 72],
    },
  ],
}

const item = (over: Partial<BottleneckItem>): BottleneckItem => ({
  course_id: 1,
  course_code: 'BIOL 108',
  course_name: 'Intro Biology',
  department: 'BIOL',
  requires_lab: false,
  expected_enrollment: 140,
  forecast: 127.8,
  forecast_hi95: 140.1,
  max_room_capacity: 150,
  largest_compatible_room: 'SCB 101',
  headroom_pct: 17.4,
  capacity_cliff_pct: 7.1,
  overflow_probability: 0.037,
  rooms_that_fit: 1,
  risk_tier: 'watch',
  remedy: {
    action: 'reserve_large_room',
    detail: 'Reserve SCB 101 (150 seats) early.',
    solver_confirmed: false,
  },
  ...over,
})

const bottlenecks: BottleneckReport = {
  meta,
  summary: {
    tier_counts: { critical: 0, high: 1, watch: 1, ok: 1 },
    tightest_cliffs: [item({}), item({ course_id: 3, course_code: 'CHEM 432', capacity_cliff_pct: 7.1 })],
    seat_band_pressure: [{ min_seats: 100, courses_needing: 2, rooms_available: 2 }],
  },
  items: [
    item({ course_id: 3, course_code: 'CHEM 432', risk_tier: 'high', overflow_probability: 0.26 }),
    item({}),
    item({ course_id: 9, course_code: 'ART 100', risk_tier: 'ok', remedy: null, capacity_cliff_pct: 80 }),
  ],
}

const metrics = (over: Partial<ScenarioMetrics> = {}): ScenarioMetrics => ({
  status: 'OPTIMAL',
  wall_time_seconds: 10,
  optimality_gap_pct: 0,
  scheduled_courses: 40,
  avg_satisfaction_pct: 97,
  min_satisfaction_pct: 80,
  satisfaction_gini: 0.0216,
  workload_gini: 0,
  slot_utilization_pct: 22.2,
  seat_occupancy_pct: 55,
  rooms_used: 11,
  instructor_loads: {},
  diagnosis: [],
  ...over,
})

const scenarioResponse = (over: Partial<ScenarioResponse> = {}): ScenarioResponse => ({
  spec: {} as ScenarioResponse['spec'],
  semester_name: 'Spring 2027',
  baseline: metrics(),
  scenario: metrics({ status: 'FEASIBLE', avg_satisfaction_pct: 96.33 }),
  diff: {
    status_before: 'OPTIMAL',
    status_after: 'FEASIBLE',
    satisfaction_delta_pct: -0.67,
    satisfaction_gini_delta: 0.0037,
    workload_gini_delta: 0,
    slot_utilization_delta_pct: 0,
    seat_occupancy_delta_pct: 0,
    changed_courses: [
      {
        course: 'CS 431 Software Eng',
        instructors_before: ['Dr. Yugyung Lee'],
        instructors_after: ['Dr. Mohammad Kuhail'],
        room_before: 'RH 204',
        room_after: 'RH 204',
        slot_before: 2,
        slot_after: 2,
      },
    ],
    absorbers: ['Dr. Mohammad Kuhail'],
    released: ['Dr. Yugyung Lee'],
    adjunct_sections: [],
  },
  notes: ['Dry run: nothing was saved.'],
  ...over,
})

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('shortSemester', () => {
  it('abbreviates the year', () => {
    expect(shortSemester('Fall 2024')).toBe("Fall '24")
  })
})

describe('ForecastPanel', () => {
  it('shows the synthetic-data warning, champion model, chart and metrics', async () => {
    vi.spyOn(insightsService, 'getForecast').mockResolvedValue(forecast)
    render(<ForecastPanel />)

    expect(await screen.findByTestId('forecast-panel')).toBeInTheDocument()
    expect(screen.getByTestId('synthetic-badge')).toBeInTheDocument()
    expect(screen.getByTestId('forecast-note')).toHaveTextContent(/SYNTHETIC/)
    expect(screen.getByTestId('champion-badge')).toHaveTextContent('damped_trend')
    expect(screen.getByTestId('forecast-chart')).toBeInTheDocument()
    expect(screen.getByTestId('forecast-summary')).toHaveTextContent('Forecast for Spring 2027: 98')
    expect(within(screen.getByTestId('model-metrics-table')).getAllByRole('row')).toHaveLength(4)
  })

  it('switches course and updates the forecast summary', async () => {
    vi.spyOn(insightsService, 'getForecast').mockResolvedValue(forecast)
    render(<ForecastPanel />)
    await screen.findByTestId('forecast-panel')
    fireEvent.change(screen.getByTestId('forecast-course-select'), { target: { value: '2' } })
    expect(screen.getByTestId('forecast-summary')).toHaveTextContent('Forecast for Spring 2027: 61')
  })

  it('shows an error instead of fabricating data when the API fails', async () => {
    vi.spyOn(insightsService, 'getForecast').mockRejectedValue(new Error('Authentication required'))
    render(<ForecastPanel />)
    expect(await screen.findByTestId('forecast-error')).toHaveTextContent('Authentication required')
    expect(screen.queryByTestId('forecast-panel')).not.toBeInTheDocument()
  })
})

describe('BottleneckBoard', () => {
  it('lists tier counts, capacity cliffs and unconfirmed remedies', async () => {
    vi.spyOn(insightsService, 'getBottlenecks').mockResolvedValue(bottlenecks)
    render(<BottleneckBoard />)

    expect(await screen.findByTestId('bottleneck-board')).toBeInTheDocument()
    expect(screen.getByTestId('tier-count-high')).toHaveTextContent('1')
    expect(within(screen.getByTestId('cliff-list')).getAllByText('+7.1%')).toHaveLength(2)
    expect(screen.getAllByText(/Not yet confirmed by the solver/i).length).toBeGreaterThan(0)
  })

  it('filters rows by risk tier', async () => {
    vi.spyOn(insightsService, 'getBottlenecks').mockResolvedValue(bottlenecks)
    render(<BottleneckBoard />)
    await screen.findByTestId('bottleneck-board')

    const table = screen.getByTestId('bottleneck-table')
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    fireEvent.change(screen.getByTestId('bottleneck-tier-filter'), { target: { value: 'high' } })
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByText('CHEM 432')).toBeInTheDocument()
    expect(within(table).queryByText('ART 100')).not.toBeInTheDocument()
  })

  it('shows an error when the report cannot be loaded', async () => {
    vi.spyOn(insightsService, 'getBottlenecks').mockRejectedValue(new Error('boom'))
    render(<BottleneckBoard />)
    expect(await screen.findByTestId('bottleneck-error')).toHaveTextContent('boom')
  })
})

describe('WhatIfPanel', () => {
  it('runs a coordinator buyout scenario and renders the before/after diff', async () => {
    vi.spyOn(insightsService, 'getInstructorNames').mockResolvedValue([
      'Dr. Mohammad Kuhail',
      'Dr. Yugyung Lee',
    ])
    const simulate = vi.spyOn(insightsService, 'simulate').mockResolvedValue(scenarioResponse())
    render(<WhatIfPanel role="coordinator" userName="Coordinator" />)

    fireEvent.click(screen.getByTestId('buyout-toggle'))
    await waitFor(() => expect(screen.getByTestId('buyout-instructor')).toHaveValue('Dr. Mohammad Kuhail'))
    fireEvent.change(screen.getByTestId('buyout-instructor'), { target: { value: 'Dr. Yugyung Lee' } })
    fireEvent.change(screen.getByTestId('coverage-strategy'), { target: { value: 'adjunct' } })
    expect(screen.getByTestId('time-limit')).toHaveValue('20')
    expect(screen.getByTestId('change-policy')).toHaveValue('minimal')
    fireEvent.change(screen.getByTestId('change-policy'), { target: { value: 'reoptimize' } })
    fireEvent.change(screen.getByTestId('time-limit'), { target: { value: '30' } })
    fireEvent.click(screen.getByTestId('run-scenario'))

    expect(await screen.findByTestId('whatif-result')).toBeInTheDocument()
    const spec = simulate.mock.calls[0][0]
    expect(spec.buyouts).toEqual([{ instructor: 'Dr. Yugyung Lee', max_courses: 1, reason: undefined }])
    expect(spec.coverage_strategy).toBe('adjunct')
    expect(spec.semester_id).toBe(6)
    expect(spec.time_limit_seconds).toBe(30)
    expect(spec.change_policy).toBe('reoptimize')

    expect(screen.getByTestId('baseline-status')).toHaveTextContent('OPTIMAL')
    expect(screen.getByTestId('scenario-status')).toHaveTextContent('FEASIBLE')
    expect(screen.getByTestId('gap-note')).toHaveTextContent(/not proven optimal/i)
    expect(screen.getByTestId('row-satisfaction')).toHaveTextContent('-0.67 pts')
    expect(screen.getByTestId('coverage-summary')).toHaveTextContent('Absorbed by: Dr. Mohammad Kuhail')
    expect(screen.getByTestId('changed-courses')).toHaveTextContent('CS 431 Software Eng')
  })

  it('shows the diagnosis for an infeasible scenario and hides the metrics table', async () => {
    vi.spyOn(insightsService, 'getInstructorNames').mockResolvedValue(['Dr. Yugyung Lee'])
    vi.spyOn(insightsService, 'simulate').mockResolvedValue(
      scenarioResponse({
        scenario: metrics({
          status: 'INFEASIBLE',
          diagnosis: ['Teaching-load arithmetic: 40 courses need 40 slots but capacity is 39.'],
        }),
      })
    )
    render(<WhatIfPanel role="coordinator" userName="Coordinator" />)
    fireEvent.click(screen.getByTestId('run-scenario'))

    expect(await screen.findByTestId('diagnosis')).toHaveTextContent('capacity is 39')
    expect(screen.queryByTestId('metrics-table')).not.toBeInTheDocument()
  })

  it('sends growth and capacity levers for coordinators', async () => {
    vi.spyOn(insightsService, 'getInstructorNames').mockResolvedValue([])
    const simulate = vi.spyOn(insightsService, 'simulate').mockResolvedValue(scenarioResponse())
    render(<WhatIfPanel role="coordinator" userName="Coordinator" />)

    fireEvent.click(screen.getByTestId('use-forecast'))
    fireEvent.click(screen.getByTestId('add-growth'))
    expect(screen.getAllByTestId('growth-row')).toHaveLength(1)
    fireEvent.change(screen.getByTestId('capacity-scale'), { target: { value: '0.9' } })
    fireEvent.click(screen.getByTestId('run-scenario'))

    await screen.findByTestId('whatif-result')
    const spec = simulate.mock.calls[0][0]
    expect(spec.use_forecast).toBe(true)
    expect(spec.enrollment_growth).toEqual([{ department: 'CS', pct: 10 }])
    expect(spec.room_capacity_scale).toBe(0.9)
    expect(spec.buyouts).toEqual([])
    expect(spec.change_policy).toBe('minimal')
  })

  it('limits faculty to their own buyout', async () => {
    const names = vi.spyOn(insightsService, 'getInstructorNames')
    const simulate = vi.spyOn(insightsService, 'simulate').mockResolvedValue(scenarioResponse())
    render(<WhatIfPanel role="instructor" userName="Dr. Yugyung Lee" />)

    expect(names).not.toHaveBeenCalled()
    expect(screen.queryByTestId('use-forecast')).not.toBeInTheDocument()
    expect(screen.queryByTestId('add-growth')).not.toBeInTheDocument()
    expect(screen.queryByTestId('capacity-scale')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('buyout-toggle'))
    expect(screen.getByTestId('buyout-self')).toHaveTextContent('Dr. Yugyung Lee')
    expect(screen.queryByTestId('buyout-instructor')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('run-scenario'))

    await screen.findByTestId('whatif-result')
    const spec = simulate.mock.calls[0][0]
    expect(spec.buyouts.map((b) => b.instructor)).toEqual(['Dr. Yugyung Lee'])
    expect(spec.enrollment_growth).toEqual([])
    expect(spec.use_forecast).toBe(false)
    expect(spec.room_capacity_scale).toBe(1)
  })

  it('surfaces simulation errors', async () => {
    vi.spyOn(insightsService, 'getInstructorNames').mockResolvedValue([])
    vi.spyOn(insightsService, 'simulate').mockRejectedValue(new Error('Faculty can only simulate their own course buyout.'))
    render(<WhatIfPanel role="coordinator" userName="Coordinator" />)
    fireEvent.click(screen.getByTestId('run-scenario'))
    expect(await screen.findByTestId('whatif-error')).toHaveTextContent('own course buyout')
  })
})

describe('InsightsPage', () => {
  it('switches between the forecast, bottleneck and what-if tabs', async () => {
    vi.spyOn(insightsService, 'getForecast').mockResolvedValue(forecast)
    vi.spyOn(insightsService, 'getBottlenecks').mockResolvedValue(bottlenecks)
    vi.spyOn(insightsService, 'getInstructorNames').mockResolvedValue([])
    render(<InsightsPage />)

    expect(await screen.findByTestId('forecast-panel')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('tab-bottlenecks'))
    expect(await screen.findByTestId('bottleneck-board')).toBeInTheDocument()
    expect(screen.queryByTestId('forecast-panel')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('tab-whatif'))
    expect(await screen.findByTestId('whatif-panel')).toBeInTheDocument()
  })
})

describe('Demo-data honesty', () => {
  it('labels the legacy analytics panel when it falls back to fixtures', async () => {
    render(<FairnessAnalyticsPanel semesterId={1} />)
    expect(await screen.findByTestId('demo-data-badge')).toHaveTextContent(/Demo data/i)
  })
})
