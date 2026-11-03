import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Refine } from '../Refine'
import { BuyoutImpact, summarizeBuyout } from '../BuyoutImpact'
import {
  ChecklistItem,
  ChecklistResult,
  ClarifyResult,
  DraftResult,
  commercializationService,
} from '../../../services/commercializationService'
import {
  DEFAULT_SCENARIO,
  ScenarioMetrics,
  ScenarioResponse,
  insightsService,
} from '../../../services/insightsService'

const draft = { fields: [], flags: [], counts: { proposed: 0, needs_author: 0, blank: 0 } } as unknown as DraftResult

const clarify: ClarifyResult = {
  note: 'Answer what you can.',
  questions: [
    {
      id: 'students',
      text: 'Did any students contribute ideas?',
      why: 'Students rights differ.',
      options: [
        { value: 'yes', label: 'Yes' },
        { value: 'no', label: 'No' },
        { value: 'unsure', label: 'Not sure' },
      ],
    },
    {
      id: 'course_release',
      text: 'Would this need a course release?',
      why: 'It affects the schedule.',
      options: [
        { value: 'yes', label: 'Yes' },
        { value: 'no', label: 'No' },
      ],
    },
  ],
}

const item = (over: Partial<ChecklistItem>): ChecklistItem => ({
  id: 'annual_disclosure',
  title: 'Check your annual outside-activity disclosure',
  status: 'review',
  why: 'Faculty disclose every year.',
  actions: ['Confirm your latest disclosure.'],
  links: [{ label: 'eCompliance disclosure', url: 'https://example.test/e' }],
  citations: [],
  tool: null,
  ...over,
})

const metrics = (over: Partial<ScenarioMetrics> = {}): ScenarioMetrics =>
  ({ status: 'OPTIMAL', diagnosis: [], ...over }) as ScenarioMetrics

const response = (over: Partial<ScenarioResponse> = {}): ScenarioResponse =>
  ({
    spec: DEFAULT_SCENARIO,
    semester_name: 'Spring 2027',
    baseline: metrics(),
    scenario: metrics(),
    diff: {
      status_before: 'OPTIMAL',
      status_after: 'OPTIMAL',
      satisfaction_delta_pct: -1.5,
      changed_courses: [{ course: 'CS 101' }],
      absorbers: [],
      released: ['Dr. Yugyung Lee'],
      adjunct_sections: ['CS 101'],
    },
    notes: [],
    ...over,
  }) as unknown as ScenarioResponse

describe('Refine (questions, checklist, buyout bridge)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('without a draft it asks for one but still offers the policy sandbox', () => {
    render(<Refine draft={null} role="coordinator" userName="" />)
    expect(screen.getByText(/Draft your disclosure in step 1/)).toBeTruthy()
    expect(screen.getByTestId('policy-input')).toBeTruthy()
    expect(screen.queryByTestId('clarify-card')).toBeNull()
  })

  it('shows questions, re-requests the checklist with the answers, and shows the buyout card only for a course release', async () => {
    vi.spyOn(commercializationService, 'clarify').mockResolvedValue(clarify)
    const checklist = vi
      .spyOn(commercializationService, 'checklist')
      .mockImplementation(async (_d, answers): Promise<ChecklistResult> => ({
        disclaimer: 'Not legal advice.',
        items: [
          ...(answers.course_release === 'yes'
            ? [item({ id: 'course_release', title: 'Course release or change in effort', status: 'action', tool: 'buyout' })]
            : []),
          item({}),
        ],
      }))

    render(<Refine draft={draft} role="instructor" userName="Dr. Yugyung Lee" />)
    await waitFor(() => expect(screen.getByTestId('question-students')).toBeTruthy())
    await waitFor(() => expect(screen.getByTestId('check-annual_disclosure')).toBeTruthy())
    expect(screen.queryByTestId('buyout-card')).toBeNull()

    fireEvent.click(screen.getByTestId('question-course_release').querySelector('input[value="yes"]')!)
    await waitFor(() => expect(screen.getByTestId('buyout-card')).toBeTruthy())
    expect(checklist).toHaveBeenLastCalledWith(draft, { course_release: 'yes' })
    // faculty cannot pick someone else: their own name is fixed
    expect(screen.getByTestId('buyout-instructor').textContent).toBe('Dr. Yugyung Lee')
  })

  it('runs the buyout dry run for the signed-in instructor and shows the solver numbers', async () => {
    const sim = vi.spyOn(insightsService, 'simulate').mockResolvedValue(response())
    render(<BuyoutImpact role="instructor" userName="Dr. Yugyung Lee" />)
    fireEvent.click(screen.getByTestId('buyout-run'))
    await waitFor(() => expect(screen.getByTestId('buyout-result')).toBeTruthy())
    const spec = sim.mock.calls[0][0]
    expect(spec.buyouts).toEqual([
      { instructor: 'Dr. Yugyung Lee', max_courses: 1, reason: 'Commercialization effort' },
    ])
    expect(spec.coverage_strategy).toBe('adjunct')
    expect(spec.semester_id).toBe(6)
    expect(screen.getByText('Feasible')).toBeTruthy()
    expect(screen.getByText(/1 course move; covered by an adjunct \(CS 101\)/)).toBeTruthy()
    expect(screen.getByText(/-1\.5 points/)).toBeTruthy()
  })

  it('lets a coordinator choose the instructor and reports an infeasible result with the diagnosis', async () => {
    vi.spyOn(insightsService, 'getInstructorNames').mockResolvedValue(['Dr. A', 'Dr. B'])
    vi.spyOn(insightsService, 'simulate').mockResolvedValue(
      response({ scenario: metrics({ status: 'INFEASIBLE', diagnosis: ['40 courses need 40 slots; 39 remain.'] }) })
    )
    render(<BuyoutImpact role="coordinator" userName="" />)
    await waitFor(() => expect((screen.getByTestId('buyout-instructor') as HTMLSelectElement).value).toBe('Dr. A'))
    fireEvent.click(screen.getByTestId('buyout-run'))
    await waitFor(() => expect(screen.getByText('Not feasible as asked')).toBeTruthy())
    expect(screen.getByText(/40 courses need 40 slots/)).toBeTruthy()
  })

  it('a failed solve is a card-level message, not a crash', async () => {
    vi.spyOn(insightsService, 'simulate').mockRejectedValue(new Error('Request timed out.'))
    render(<BuyoutImpact role="instructor" userName="Dr. Yugyung Lee" />)
    fireEvent.click(screen.getByTestId('buyout-run'))
    await waitFor(() => expect(screen.getByText('Request timed out.')).toBeTruthy())
    expect(screen.queryByTestId('buyout-result')).toBeNull()
  })

  it('summarizeBuyout names a colleague absorber and handles a missing satisfaction delta', () => {
    const res = response()
    res.diff.adjunct_sections = []
    res.diff.absorbers = ['Colleague']
    res.diff.satisfaction_delta_pct = null
    const s = summarizeBuyout(res)
    expect(s.feasible).toBe(true)
    expect(s.detail[0]).toContain('covered by Colleague')
    expect(s.detail[1]).toContain('not available')
  })
})
