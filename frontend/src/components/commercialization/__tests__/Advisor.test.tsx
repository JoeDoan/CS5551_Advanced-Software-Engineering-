import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AdvisorBox } from '../AdvisorBox'
import { GlossaryDrawer, matchesEntry } from '../GlossaryDrawer'
import { ReadinessCoachCard, TITLES } from '../ReadinessCoachCard'
import {
  AdvisorResponse,
  DraftResult,
  GlossaryEntry,
  ReadinessDimension,
  ReadinessResult,
  commercializationService,
} from '../../../services/commercializationService'

const draft = { fields: [], flags: [], counts: { proposed: 0, needs_author: 0, blank: 0 } } as unknown as DraftResult

const DRAFT_LABEL = 'General explainer, draft, not yet reviewed by the technology office'

const concept: AdvisorResponse = {
  intent: 'concept',
  blocks: [
    {
      type: 'glossary',
      source_label: DRAFT_LABEL,
      title: 'Prior art',
      body: 'Anything made public before filing.\n\nExample: an acoustic sensor.\n\nThink about: What is closest?',
      citations: [],
      next_questions: ['What is novelty?'],
    },
  ],
}

const referral: AdvisorResponse = {
  intent: 'referral',
  blocks: [
    {
      type: 'referral',
      source_label: 'Referral: needs the technology office or the conflict of interest office',
      title: 'This one is for the technology office',
      body: 'Whether an invention is patentable is a legal judgment.\n\nWhat to bring: your draft.',
      citations: [],
      next_questions: [],
    },
    { ...concept.blocks[0], title: 'Patentability' },
  ],
}

describe('AdvisorBox', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows every block with its source label and marks glossary text as a draft', async () => {
    const ask = vi.spyOn(commercializationService, 'askAdvisor').mockResolvedValue(concept)
    render(<AdvisorBox />)
    fireEvent.change(screen.getByTestId('advisor-input'), { target: { value: 'What is prior art?' } })
    fireEvent.click(screen.getByTestId('advisor-ask'))
    await waitFor(() => expect(screen.getByTestId('advisor-answer')).toBeTruthy())
    expect(ask).toHaveBeenCalledWith('What is prior art?')
    expect(screen.getByTestId('advisor-answer').getAttribute('data-intent')).toBe('concept')
    expect(screen.getByTestId('source-label').textContent).toBe(DRAFT_LABEL)
    expect(screen.getByText('Example: an acoustic sensor.')).toBeTruthy()
  })

  it('renders a referral first and visibly different from an explanation', async () => {
    vi.spyOn(commercializationService, 'askAdvisor').mockResolvedValue(referral)
    render(<AdvisorBox />)
    fireEvent.change(screen.getByTestId('advisor-input'), { target: { value: 'Is my invention patentable?' } })
    fireEvent.click(screen.getByTestId('advisor-ask'))
    await waitFor(() => expect(screen.getByTestId('block-referral')).toBeTruthy())
    expect(screen.getByTestId('block-referral').className).toContain('border-amber')
    expect(screen.queryByTestId('block-policy_quote')).toBeNull()
    const blocks = screen.getByTestId('advisor-answer').children
    expect(within(blocks[0] as HTMLElement).getByText(/This one is for the technology office/)).toBeTruthy()
  })

  it('follow-up chips ask that question and the example chips only fill the box', async () => {
    const ask = vi.spyOn(commercializationService, 'askAdvisor').mockResolvedValue(concept)
    render(<AdvisorBox />)
    fireEvent.click(screen.getByText('Is my invention patentable?'))
    expect((screen.getByTestId('advisor-input') as HTMLInputElement).value).toBe('Is my invention patentable?')
    expect(ask).not.toHaveBeenCalled()

    fireEvent.click(screen.getByText('What is prior art?'))
    fireEvent.click(screen.getByTestId('advisor-ask'))
    await waitFor(() => expect(screen.getByTestId('chip')).toBeTruthy())
    fireEvent.click(screen.getByTestId('chip'))
    await waitFor(() => expect(ask).toHaveBeenLastCalledWith('What is novelty?'))
    expect((screen.getByTestId('advisor-input') as HTMLInputElement).value).toBe('What is novelty?')
  })

  it('does not send a question shorter than three characters, and shows a failed request plainly', async () => {
    const ask = vi.spyOn(commercializationService, 'askAdvisor').mockRejectedValue(new Error('Server unavailable.'))
    render(<AdvisorBox />)
    fireEvent.change(screen.getByTestId('advisor-input'), { target: { value: 'hi' } })
    expect((screen.getByTestId('advisor-ask') as HTMLButtonElement).disabled).toBe(true)
    fireEvent.keyDown(screen.getByTestId('advisor-input'), { key: 'Enter' })
    expect(ask).not.toHaveBeenCalled()

    fireEvent.change(screen.getByTestId('advisor-input'), { target: { value: 'What is novelty?' } })
    fireEvent.click(screen.getByTestId('advisor-ask'))
    await waitFor(() => expect(screen.getByText('Server unavailable.')).toBeTruthy())
    expect(screen.queryByTestId('advisor-answer')).toBeNull()
  })
})

const dim = (over: Partial<ReadinessDimension> & Pick<ReadinessDimension, 'id'>): ReadinessDimension => ({
  status: 'not_found',
  quote: null,
  follow_up: null,
  needs_author: true,
  ...over,
})

const readiness = (): ReadinessResult => ({
  note: 'No score and no verdict. This lists what the disclosure does not yet say.',
  dimensions: [
    dim({ id: 'problem', status: 'stated', quote: 'Bridge inspection is slow.', needs_author: false }),
    dim({ id: 'application', status: 'partly', follow_up: 'Who would use this, and what do they do today instead?' }),
    dim({ id: 'difference', status: 'not_found', follow_up: 'What is the closest existing alternative?' }),
    dim({ id: 'evidence', status: 'not_found', follow_up: 'What has been built or tested so far?' }),
    dim({ id: 'related_work', status: 'partly', quote: '[1] Smith, P. Ultrasonic inspection.', follow_up: 'Which is closest?' }),
    dim({ id: 'timing', status: 'stated', quote: 'March 3, 2025', needs_author: true }),
  ],
})

describe('ReadinessCoachCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows six dimensions with quotes and one follow-up per gap, and no score', async () => {
    const spy = vi.spyOn(commercializationService, 'readiness').mockResolvedValue(readiness())
    render(<ReadinessCoachCard draft={draft} />)
    await waitFor(() => expect(screen.getByTestId('dimension-problem')).toBeTruthy())
    expect(spy).toHaveBeenCalledWith(draft, '', [])
    for (const id of Object.keys(TITLES)) expect(screen.getByTestId(`dimension-${id}`)).toBeTruthy()
    expect(screen.getByText(/From your text: “Bridge inspection is slow\.”/)).toBeTruthy()
    expect(screen.getByText('Who would use this, and what do they do today instead?')).toBeTruthy()
    // a stated dimension asks nothing; a missing one is described neutrally, not as a failure
    expect(within(screen.getByTestId('dimension-problem')).queryByText(/\?/)).toBeNull()
    expect(within(screen.getByTestId('dimension-difference')).getByText('Not found in your text')).toBeTruthy()
    expect(screen.getByText(/No score and no verdict/)).toBeTruthy()
    expect(screen.getByTestId('readiness-card').textContent).not.toMatch(/\bscore:|\d+\s*\/\s*\d+|\d+%/i)
    // a date found in the paper still has to be confirmed by the author
    expect(within(screen.getByTestId('dimension-timing')).getByText('Needs your confirmation')).toBeTruthy()
  })

  it('sends extra text only when asked to, and says it is not saved', async () => {
    const spy = vi.spyOn(commercializationService, 'readiness').mockResolvedValue(readiness())
    render(<ReadinessCoachCard draft={draft} />)
    await waitFor(() => expect(screen.getByTestId('dimension-problem')).toBeTruthy())
    fireEvent.change(screen.getByTestId('readiness-extra'), { target: { value: 'We tested it on two bridges.' } })
    expect(spy).toHaveBeenCalledTimes(1) // typing alone sends nothing
    expect(screen.getByText(/It is not saved/)).toBeTruthy()
    fireEvent.click(screen.getByTestId('readiness-update'))
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(draft, 'We tested it on two bridges.', []))
  })

  it('marking a dimension covered elsewhere re-reads with it and drops its prompt', async () => {
    const spy = vi.spyOn(commercializationService, 'readiness').mockImplementation(async (_d, _e, covered) => {
      const r = readiness()
      r.dimensions = r.dimensions.map((d) =>
        covered.includes(d.id) ? { ...d, follow_up: null, needs_author: false } : d
      )
      return r
    })
    render(<ReadinessCoachCard draft={draft} />)
    await waitFor(() => expect(screen.getByTestId('dimension-evidence')).toBeTruthy())
    fireEvent.click(within(screen.getByTestId('dimension-evidence')).getByRole('checkbox'))
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(draft, '', ['evidence']))
    await waitFor(() =>
      expect(within(screen.getByTestId('dimension-evidence')).getByText(/marked this as covered elsewhere/)).toBeTruthy()
    )
    expect(screen.queryByText('What has been built or tested so far?')).toBeNull()
  })

  it('shows a failed read as a message, not a crash', async () => {
    vi.spyOn(commercializationService, 'readiness').mockRejectedValue(new Error('Could not read the draft.'))
    render(<ReadinessCoachCard draft={draft} />)
    await waitFor(() => expect(screen.getByText('Could not read the draft.')).toBeTruthy())
  })
})

const entry = (over: Partial<GlossaryEntry>): GlossaryEntry => ({
  id: 'novelty',
  term: 'Novelty',
  aliases: ['novel'],
  plain: 'Whether it was already public.',
  example: 'A method that adds one known step.',
  think_about: ['What does mine do differently?'],
  related_fields: [],
  related: [],
  reviewed_by: null,
  reviewed_on: null,
  source_label: DRAFT_LABEL,
  ...over,
})

describe('GlossaryDrawer', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads entries only when opened, labels drafts, and filters by term or alias', async () => {
    const list = vi
      .spyOn(commercializationService, 'glossary')
      .mockResolvedValue([
        entry({}),
        entry({ id: 'prior_art', term: 'Prior art', aliases: ['related work'], example: 'Ultrasonic inspection papers.' }),
      ])
    render(<GlossaryDrawer />)
    expect(list).not.toHaveBeenCalled()
    fireEvent.click(screen.getByTestId('glossary-open'))
    await waitFor(() => expect(screen.getByTestId('glossary-novelty')).toBeTruthy())
    expect(list).toHaveBeenCalledTimes(1)
    expect(within(screen.getByTestId('glossary-novelty')).getByText(DRAFT_LABEL)).toBeTruthy()
    expect(screen.getByText('Example: A method that adds one known step.')).toBeTruthy()

    fireEvent.change(screen.getByTestId('glossary-search'), { target: { value: 'related' } })
    expect(screen.queryByTestId('glossary-novelty')).toBeNull()
    expect(screen.getByTestId('glossary-prior_art')).toBeTruthy()
    fireEvent.change(screen.getByTestId('glossary-search'), { target: { value: 'zzz' } })
    expect(screen.getByText(/No term matches/)).toBeTruthy()
  })

  it('shows a load failure and matchesEntry treats an empty query as everything', async () => {
    vi.spyOn(commercializationService, 'glossary').mockRejectedValue(new Error('Glossary unavailable.'))
    render(<GlossaryDrawer />)
    fireEvent.click(screen.getByTestId('glossary-open'))
    await waitFor(() => expect(screen.getByText('Glossary unavailable.')).toBeTruthy())
    expect(matchesEntry(entry({}), '')).toBe(true)
    expect(matchesEntry(entry({}), 'NOVEL')).toBe(true)
    expect(matchesEntry(entry({}), 'patent')).toBe(false)
  })
})
