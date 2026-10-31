import { apiClient } from './apiClient'

export interface HistoryPoint {
  semester_id: number
  semester_name: string
  enrolled: number
  waitlist: number
}

export interface ModelMetrics {
  mae: number
  smape_pct: number
  last_origin_mae: number
  last_origin_smape_pct: number
}

export interface CourseForecast {
  course_id: number
  course_code: string
  course_name: string
  department: string
  history: HistoryPoint[]
  forecasts: Record<string, number>
  forecast: number
  interval_80: [number, number]
  interval_95: [number, number]
}

export interface ForecastMeta {
  target_semester_id: number
  target_semester_name: string
  observed_semester_ids: number[]
  backtest_origins: number[]
  champion_model: string
  interval_calibration_n: number
  held_out_coverage_80: number | null
  data_source: string
  is_synthetic: boolean
  methodology: string
  note: string | null
}

export interface EnrollmentForecast {
  meta: ForecastMeta
  model_metrics: Record<string, ModelMetrics>
  courses: CourseForecast[]
  skipped_course_ids: number[]
}

export type RiskTier = 'critical' | 'high' | 'watch' | 'ok'

export interface Remedy {
  action: string
  detail: string
  solver_confirmed: boolean
}

export interface BottleneckItem {
  course_id: number
  course_code: string
  course_name: string
  department: string
  requires_lab: boolean
  expected_enrollment: number
  forecast: number
  forecast_hi95: number
  max_room_capacity: number
  largest_compatible_room: string
  headroom_pct: number
  capacity_cliff_pct: number
  overflow_probability: number
  rooms_that_fit: number
  risk_tier: RiskTier
  remedy: Remedy | null
}

export interface SeatBandPressure {
  min_seats: number
  courses_needing: number
  rooms_available: number
}

export interface BottleneckReport {
  meta: ForecastMeta
  summary: {
    tier_counts: Record<RiskTier, number>
    tightest_cliffs: BottleneckItem[]
    seat_band_pressure: SeatBandPressure[]
  }
  items: BottleneckItem[]
}

export type CoverageStrategy = 'none' | 'overload' | 'adjunct'
export type ChangePolicy = 'minimal' | 'reoptimize'

export interface ScenarioSpec {
  semester_id: number
  use_forecast: boolean
  enrollment_growth: { department: string; pct: number }[]
  buyouts: { instructor: string; max_courses: number; reason?: string }[]
  coverage_strategy: CoverageStrategy
  room_capacity_scale: number
  blocked_room_slots: { room_number: string; slot_id: number; reason?: string }[]
  change_policy: ChangePolicy
  time_limit_seconds: number
}

export interface ScenarioMetrics {
  status: string
  wall_time_seconds: number
  optimality_gap_pct: number | null
  scheduled_courses: number
  avg_satisfaction_pct: number | null
  min_satisfaction_pct: number | null
  satisfaction_gini: number | null
  workload_gini: number | null
  slot_utilization_pct: number | null
  seat_occupancy_pct: number | null
  rooms_used: number
  instructor_loads: Record<string, number>
  diagnosis: string[]
}

export interface CourseChange {
  course: string
  instructors_before: string[]
  instructors_after: string[]
  room_before: string
  room_after: string
  slot_before: number
  slot_after: number
}

export interface ScenarioDiff {
  status_before: string
  status_after: string
  satisfaction_delta_pct: number | null
  satisfaction_gini_delta: number | null
  workload_gini_delta: number | null
  slot_utilization_delta_pct: number | null
  seat_occupancy_delta_pct: number | null
  changed_courses: CourseChange[]
  absorbers: string[]
  released: string[]
  adjunct_sections: string[]
}

export interface ScenarioResponse {
  spec: ScenarioSpec
  semester_name: string
  baseline: ScenarioMetrics
  scenario: ScenarioMetrics
  diff: ScenarioDiff
  notes: string[]
}

export const DEFAULT_SCENARIO: ScenarioSpec = {
  semester_id: 6,
  use_forecast: false,
  enrollment_growth: [],
  buyouts: [],
  coverage_strategy: 'overload',
  room_capacity_scale: 1,
  blocked_room_slots: [],
  change_policy: 'minimal',
  time_limit_seconds: 20,
}

// A cold baseline can take up to a minute to solve; do not use the 10s default.
const SOLVE_TIMEOUT_MS = 180_000

export const insightsService = {
  async getForecast(): Promise<EnrollmentForecast> {
    const res = await apiClient.get<EnrollmentForecast>('/forecast/enrollment')
    return res.data
  },

  async getBottlenecks(): Promise<BottleneckReport> {
    const res = await apiClient.get<BottleneckReport>('/forecast/bottlenecks')
    return res.data
  },

  async simulate(spec: ScenarioSpec): Promise<ScenarioResponse> {
    const res = await apiClient.post<ScenarioResponse>('/scenarios/simulate', spec, {
      timeout: SOLVE_TIMEOUT_MS,
    })
    return res.data
  },

  async getInstructorNames(): Promise<string[]> {
    const res = await apiClient.get<{ full_name: string }[]>('/instructors')
    return res.data.map((i) => i.full_name).sort()
  },
}

export interface CopilotStatus {
  llm_enabled: boolean
  model: string | null
  note: string
}

export interface ParseResult {
  prompt: string
  parser_used: 'llm' | 'rules'
  llm_status: string
  spec: ScenarioSpec
  warnings: string[]
  understood: boolean
  rules_agree: boolean | null
}

export interface AskResult {
  parse: ParseResult | null
  result: ScenarioResponse
  explanation: string[]
}

export const copilotService = {
  async getStatus(): Promise<CopilotStatus> {
    const res = await apiClient.get<CopilotStatus>('/copilot/status')
    return res.data
  },

  async parse(prompt: string, useLlm: boolean): Promise<ParseResult> {
    // Claude can take several seconds; the 10s default timeout is too short.
    const res = await apiClient.post<ParseResult>(
      '/copilot/parse',
      { prompt, use_llm: useLlm },
      { timeout: 90_000 }
    )
    return res.data
  },

  async ask(spec: ScenarioSpec): Promise<AskResult> {
    const res = await apiClient.post<AskResult>('/copilot/ask', { spec }, { timeout: SOLVE_TIMEOUT_MS })
    return res.data
  },
}

// Course names in the seed data already start with the course code.
export const courseLabel = (code: string, name: string): string =>
  name.startsWith(code) ? name : `${code} ${name}`

export const errorMessage = (err: unknown): string =>
  err instanceof Error && err.message ? err.message : 'Request failed. Please try again.'

export default insightsService
