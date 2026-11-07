import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Refine } from '../Refine'
import { BuyoutImpact, summarizeBuyout } from '../BuyoutImpact'
import {
  AdvisorResponse,
  ChecklistItem,
  ChecklistResult,
  ClarifyResult,
  DraftResult,
  ReadinessResult,
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

const readinessFixture: ReadinessResult = {
  note: 'No score and no verdict. This lists what the disclosure does not yet say.',
  dimensions: [
    {
      id: 'problem',
      status: 'stated',
      quote: 'Manual bridge deck inspection misses early subsurface micro-cracks.',
      follow_up: null,
      needs_author: false,
    },
    {
      id: 'application',
      status: 'partly',
      quote: 'Highway bridge maintenance',
      follow_up: 'Who is the specific user or operator, and what changes in their workflow?',
      needs_author: true,
    },
    {
      id: 'difference',
      status: 'stated',
      quote: 'Uses low-cost piezoelectric array instead of laser vibrometry.',
      follow_up: null,
      needs_author: false,
    },
    {
      id: 'evidence',
      status: 'not_found',
      quote: null,
      follow_up: 'What data, simulation, or prototype results exist so far?',
      needs_author: true,
    },
    {
      id: 'related_work',
      status: 'partly',
      quote: 'Smith et al. 2022 acoustic emission study',
      follow_up: 'Which closest papers, patents, or existing tools should the office compare against?',
      needs_author: true,
    },
    {
      id: 'timing',
      status: 'not_found',
      quote: null,
      follow_up: 'Are any talks, posters, preprints, or theses planned in the next 3 to 6 months?',
      needs_author: true,
    },
  ],
}

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
    vi.spyOn(commercializationService, 'getReadiness').mockResolvedValue(readinessFixture)
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

  it('renders advisor blocks with source_label badges and triggers askAdvisor when clicking next_questions chips', async () => {
    const firstResponse: AdvisorResponse = {
      intent: 'concept',
      blocks: [
        {
          type: 'glossary',
          source_label: 'General explainer, draft, not yet reviewed by the technology office',
          title: 'Conflict of interest',
          body: 'An outside financial interest or role that could affect university duties.',
          next_questions: ['When do I report outside consulting?'],
        },
        {
          type: 'referral',
          source_label: 'Referral: needs the technology office or the conflict of interest office',
          title: 'Campus review required',
          body: 'Contact the UMKC Conflict of Interest Office (umkccoi@umkc.edu) for case-specific determinations.',
        },
      ],
    }

    const followUpResponse: AdvisorResponse = {
      intent: 'policy',
      blocks: [
        {
          type: 'policy_quote',
          source_label: 'Quoted policy (UM Collected Rules 330.015, Amended 9-12-24)',
          title: 'Outside interest reporting',
          body: 'Found 1 passage that may be relevant.',
          citations: [
            {
              passage_id: 'um-crr-330-015#4',
              source_title: 'UM Collected Rules 330.015, Policy on Conflict of Interest',
              source_url: 'https://example.test/330.015',
              version: 'Amended 9-12-24',
              applies_to: 'All University of Missouri System employees',
              section: '330.015',
              locator: '330.015',
              text: 'They shall inform their chairpersons/supervisors in writing of their Outside Interests.',
              score: 11.2,
            },
          ],
        },
      ],
    }

    const askAdvisor = vi
      .spyOn(commercializationService, 'askAdvisor')
      .mockResolvedValueOnce(firstResponse)
      .mockResolvedValueOnce(followUpResponse)

    render(<Refine draft={null} role="instructor" userName="Dr. Yugyung Lee" />)
    fireEvent.change(screen.getByTestId('policy-input'), {
      target: { value: 'What is a conflict of interest?' },
    })
    fireEvent.click(screen.getByTestId('policy-ask'))

    await waitFor(() => expect(screen.getByTestId('policy-answer')).toBeTruthy())
    expect(askAdvisor).toHaveBeenCalledWith('What is a conflict of interest?', null)
    const badges = screen.getAllByTestId('advisor-source-badge')
    expect(badges[0].textContent).toBe(
      'General explainer, draft, not yet reviewed by the technology office'
    )
    expect(badges[1].textContent).toBe(
      'Referral: needs the technology office or the conflict of interest office'
    )

    fireEvent.click(screen.getByTestId('advisor-next-question'))
    await waitFor(() =>
      expect(askAdvisor).toHaveBeenCalledWith('When do I report outside consulting?', null)
    )
    await waitFor(() =>
      expect(screen.getByText('Quoted policy (UM Collected Rules 330.015, Amended 9-12-24)')).toBeTruthy()
    )
  })

  it('renders ReadinessCoachCard with 6 dimensions, quotes, follow-ups, and re-queries getReadiness on extra text submit', async () => {
    vi.spyOn(commercializationService, 'clarify').mockResolvedValue(clarify)
    vi.spyOn(commercializationService, 'checklist').mockResolvedValue({
      disclaimer: 'Not legal advice.',
      items: [],
    })
    const getReadiness = vi
      .spyOn(commercializationService, 'getReadiness')
      .mockResolvedValueOnce(readinessFixture)
      .mockResolvedValueOnce({
        ...readinessFixture,
        dimensions: readinessFixture.dimensions.map((d) =>
          d.id === 'evidence'
            ? {
                ...d,
                status: 'stated',
                quote: 'Validated on 12 bridge deck cores in the structures lab.',
                follow_up: null,
                needs_author: false,
              }
            : d
        ),
      })

    render(<Refine draft={draft} role="instructor" userName="Dr. Yugyung Lee" />)
    await waitFor(() => expect(screen.getByTestId('readiness-coach-card')).toBeTruthy())
    expect(getReadiness).toHaveBeenCalledWith(draft, '')

    for (const id of ['problem', 'application', 'difference', 'evidence', 'related_work', 'timing']) {
      expect(screen.getByTestId(`readiness-dim-${id}`)).toBeTruthy()
    }
    expect(
      screen.getByText(/From your draft: “Manual bridge deck inspection misses early subsurface micro-cracks.”/)
    ).toBeTruthy()
    expect(
      screen.getByText('What data, simulation, or prototype results exist so far?')
    ).toBeTruthy()

    fireEvent.change(screen.getByTestId('readiness-extra-input'), {
      target: { value: 'Validated on 12 bridge deck cores in the structures lab.' },
    })
    fireEvent.click(screen.getByTestId('readiness-update-button'))

    await waitFor(() =>
      expect(getReadiness).toHaveBeenCalledWith(
        draft,
        'Validated on 12 bridge deck cores in the structures lab.'
      )
    )
    await waitFor(() =>
      expect(screen.getByTestId('readiness-status-evidence').textContent).toBe('stated')
    )
  })

  it('opens GlossaryDrawer from Refine, displays the draft source badge, and filters entries by search term', async () => {
    vi.spyOn(commercializationService, 'getGlossary').mockResolvedValue({
      source_label: 'General explainer, draft, not yet reviewed by the technology office',
      entries: [
        {
          term: 'Novelty',
          plain: 'What is new compared with prior public disclosures.',
          example: 'A sensor array that isolates micro-crack frequencies.',
          what_office_asks: 'What step has not been published before?',
          related_fields: ['A1_novel'],
          reviewed_by: null,
          reviewed_on: null,
        },
        {
          term: 'Inventorship',
          plain: 'Legal determination of who conceived the claimed invention.',
          example: 'Co-designing the signal filter vs running standard tests.',
          what_office_asks: 'Who conceived the technical solution?',
          related_fields: ['B_contributors'],
          reviewed_by: null,
          reviewed_on: null,
        },
      ],
    })

    render(<Refine draft={null} role="instructor" userName="Dr. Yugyung Lee" />)
    fireEvent.click(screen.getByTestId('open-glossary-button'))

    await waitFor(() => expect(screen.getByTestId('glossary-drawer')).toBeTruthy())
    expect(screen.getByTestId('glossary-source-badge').textContent).toBe(
      'General explainer, draft, not yet reviewed by the technology office'
    )
    expect(screen.getByTestId('glossary-entry-novelty')).toBeTruthy()
    expect(screen.getByTestId('glossary-entry-inventorship')).toBeTruthy()

    fireEvent.change(screen.getByTestId('glossary-search'), {
      target: { value: 'inventorship' },
    })
    expect(screen.queryByTestId('glossary-entry-novelty')).toBeNull()
    expect(screen.getByTestId('glossary-entry-inventorship')).toBeTruthy()
  })
})
