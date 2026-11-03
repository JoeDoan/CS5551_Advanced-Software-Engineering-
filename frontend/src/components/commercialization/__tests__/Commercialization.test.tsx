import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CommercializationPage } from '../../../pages/CommercializationPage'
import { suggestTerms } from '../Validate'
import {
  CommercializationStatus,
  DraftField,
  DraftResult,
  MatchResult,
  PolicyAnswer,
  commercializationService,
} from '../../../services/commercializationService'

const status: CommercializationStatus = {
  llm_enabled: false,
  model: null,
  privacy_note: 'Your document is processed in memory and is not saved.',
  idf_fields: 26,
  policy_note: 'Not legal advice.',
}

const field = (over: Partial<DraftField>): DraftField => ({
  id: 'A1_title',
  section: 'A.1',
  label: 'Title',
  fill: 'extract',
  status: 'proposed',
  value: '',
  evidence: '',
  note: '',
  ...over,
})

const draft = (): DraftResult => ({
  extractor: 'rules',
  llm_status: 'disabled',
  pages_read: 2,
  chars_read: 5000,
  fields: [
    field({ value: 'Low-cost Acoustic Sensing of Bridge Cracks', evidence: 'Low-cost Acoustic Sensing' }),
    field({
      id: 'A1_keywords',
      label: 'Keywords',
      value: 'acoustic sensing; structural health monitoring; bridges',
      evidence: 'Keywords: acoustic sensing',
    }),
    field({
      id: 'E_submitter',
      section: 'E',
      label: 'Signature',
      fill: 'human',
      status: 'blank',
    }),
  ],
  flags: [{ level: 'deadline', message: 'The one-year U.S. patent window appears to have ended.' }],
  counts: { proposed: 1, needs_author: 0, blank: 1 },
  warnings: [],
  privacy_note: '',
  form_url: 'https://example.test/form.docx',
  returns_to: 'Office of Technology Commercialization',
})

const matchResult = (): MatchResult => ({
  matched: true,
  matches: [
    {
      id: 'infrastructure-monitoring',
      name: 'Infrastructure inspection and monitoring',
      score: 4,
      matched_terms: ['bridge', 'crack'],
      naics: [{ code: '237310', title: 'Highway, Street, and Bridge Construction' }],
      pain_points: ['Manual inspection is slow.'],
      buyer_types: ['State transportation departments'],
      sbir_agencies: ['NSF'],
    },
  ],
  message: 'These are starting points.',
  note: 'Not market research.',
  naics_source: 'https://www.census.gov/naics/',
  sbir_topics_url: 'https://www.sbir.gov/topics',
})

const policy = (over: Partial<PolicyAnswer> = {}): PolicyAnswer => ({
  answered: true,
  question: 'q',
  citations: [
    {
      passage_id: 'um-crr-100-020#9',
      source_title: 'UM Collected Rules 100.020, Invention and Patent Regulations',
      source_url: 'https://example.test/100.020',
      version: 'Amended 6-24-21',
      applies_to: 'University employees and enrolled students',
      section: '100.020',
      locator: '100.020',
      text: 'These regulations constitute a term and condition of enrollment.',
      score: 12,
    },
  ],
  matched_terms: ['student'],
  message: 'Found 1 passage(s) that may be relevant.',
  disclaimer: 'This is not legal advice.',
  corpus_note: '',
  corpus_passages: 425,
  ...over,
})

describe('CommercializationPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(commercializationService, 'getStatus').mockResolvedValue(status)
  })

  it('drafts from pasted text and shows evidence, flags and blank fields', async () => {
    const spy = vi.spyOn(commercializationService, 'draftFromText').mockResolvedValue(draft())
    render(<CommercializationPage />)
    fireEvent.change(screen.getByTestId('paste-input'), { target: { value: 'A manuscript about bridges.' } })
    fireEvent.click(screen.getByTestId('draft-button'))
    await waitFor(() => expect(screen.getByTestId('draft-result')).toBeTruthy())
    expect(spy).toHaveBeenCalledWith('A manuscript about bridges.', false)
    expect(screen.getByText(/appears to have ended/)).toBeTruthy()
    expect(screen.getByText(/From your document: “Low-cost Acoustic Sensing”/)).toBeTruthy()
    expect(screen.getByTestId('field-E_submitter').textContent).toContain('Yours to fill')
  })

  it('never offers Claude unless the server has it, and warns that text is sent', async () => {
    render(<CommercializationPage />)
    await waitFor(() => expect(commercializationService.getStatus).toHaveBeenCalled())
    expect((screen.getByTestId('use-llm') as HTMLInputElement).disabled).toBe(true)

    vi.spyOn(commercializationService, 'getStatus').mockResolvedValue({ ...status, llm_enabled: true, model: 'm' })
    render(<CommercializationPage />)
    await waitFor(() =>
      expect((screen.getAllByTestId('use-llm')[1] as HTMLInputElement).disabled).toBe(false)
    )
    expect(screen.getAllByText(/sends your document text to Anthropic/)[0]).toBeTruthy()
  })

  it('shows policy citations with source and version, and refusals plainly', async () => {
    const ask = vi.spyOn(commercializationService, 'askPolicy').mockResolvedValue(policy())
    render(<CommercializationPage />)
    fireEvent.click(screen.getByTestId('step-refine'))
    fireEvent.change(screen.getByTestId('policy-input'), { target: { value: 'Can my PhD student help?' } })
    fireEvent.click(screen.getByTestId('policy-ask'))
    await waitFor(() => expect(screen.getByTestId('policy-answer')).toBeTruthy())
    expect(ask).toHaveBeenCalledWith('Can my PhD student help?')
    expect(screen.getByText(/Amended 6-24-21/)).toBeTruthy()
    expect(screen.getByText(/This is not legal advice/)).toBeTruthy()

    ask.mockResolvedValue(policy({ answered: false, citations: [], message: 'No passage in the loaded policies answers this.' }))
    fireEvent.click(screen.getByTestId('policy-ask'))
    await waitFor(() => expect(screen.getByText(/No passage in the loaded policies/)).toBeTruthy())
  })

  it('Stage 3 asks for a draft first, then lists markets and exactly what would be sent', async () => {
    vi.spyOn(commercializationService, 'draftFromText').mockResolvedValue(draft())
    const match = vi.spyOn(commercializationService, 'match').mockResolvedValue(matchResult())
    render(<CommercializationPage />)
    fireEvent.click(screen.getByTestId('step-validate'))
    expect(screen.getByText(/Draft your disclosure in step 1 first/)).toBeTruthy()

    fireEvent.click(screen.getByTestId('step-drop'))
    fireEvent.change(screen.getByTestId('paste-input'), { target: { value: 'A manuscript about bridges.' } })
    fireEvent.click(screen.getByTestId('draft-button'))
    await waitFor(() => expect(screen.getByTestId('draft-result')).toBeTruthy())

    fireEvent.click(screen.getByTestId('step-validate'))
    await waitFor(() => expect(screen.getByTestId('market-infrastructure-monitoring')).toBeTruthy())
    expect(match).toHaveBeenCalled()
    expect(match.mock.calls[0][0]).toContain('Low-cost Acoustic Sensing')
    expect(screen.getByText(/NAICS: 237310/)).toBeTruthy()

    // the user controls what leaves the session; nothing is looked up until the button is pressed
    const lookup = vi.spyOn(commercializationService, 'lookup').mockResolvedValue({
      mode: 'fixture',
      terms: [],
      retrieved: '2026-11-02',
      items: [
        { kind: 'literature', title: 'Acoustic inspection of decks', year: 1999, source: 'OpenAlex', url: '', detail: '' },
      ],
      message: 'Saved results from 2026-11-02 for 1 related items.',
      note: 'Not a novelty or patentability finding.',
    })
    expect(lookup).not.toHaveBeenCalled()
    expect(screen.getByTestId('will-send').textContent).toContain('acoustic sensing')
    fireEvent.click(screen.getByLabelText('Remove acoustic sensing'))
    expect(screen.getByTestId('will-send').textContent).not.toContain('acoustic sensing')
    const sent = screen.getByTestId('will-send').textContent!.replace('Will send: ', '').split(', ')
    fireEvent.click(screen.getByTestId('lookup-button'))
    await waitFor(() => expect(screen.getByTestId('lookup-result')).toBeTruthy())
    expect(lookup).toHaveBeenCalledWith(sent)
    expect(screen.getByText(/Saved results, not a live search/)).toBeTruthy()
    expect(screen.getByText('Acoustic inspection of decks')).toBeTruthy()
  })
})

describe('suggestTerms', () => {
  it('uses short keyword phrases only and caps the list at five', () => {
    const d = draft()
    d.fields[1].value =
      'acoustic sensing; Inhibition of Target-X via Novel Compound Y-12 in vivo models; bridges; a; b; c; d; e'
    const terms = suggestTerms(d, null)
    expect(terms).not.toContain('inhibition of target-x via novel compound y-12 in vivo models')
    expect(terms.length).toBeLessThanOrEqual(5)
    expect(terms[0]).toBe('acoustic sensing')
  })
})
