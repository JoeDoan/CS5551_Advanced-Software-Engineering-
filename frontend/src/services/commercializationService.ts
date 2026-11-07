import { apiClient } from './apiClient'

export type FillMode = 'extract' | 'extract_verify' | 'human'
export type FieldStatus = 'proposed' | 'needs_author' | 'blank'

export interface DraftField {
  id: string
  section: string
  label: string
  fill: FillMode
  status: FieldStatus
  value: string
  evidence: string
  note: string
}

export interface DraftFlag {
  level: 'info' | 'warning' | 'deadline'
  message: string
}

export interface DraftResult {
  extractor: 'rules' | 'claude'
  llm_status: string
  pages_read: number
  chars_read: number
  fields: DraftField[]
  flags: DraftFlag[]
  counts: Record<FieldStatus, number>
  warnings: string[]
  privacy_note: string
  form_url: string
  returns_to: string
}

export interface PolicyCitation {
  passage_id: string
  source_title: string
  source_url: string
  version: string
  applies_to: string
  section: string
  locator: string
  text: string
  score: number
}

export interface PolicyAnswer {
  answered: boolean
  question: string
  citations: PolicyCitation[]
  matched_terms: string[]
  message: string
  disclaimer: string
  corpus_note: string
  corpus_passages: number
}

export interface IndustryMatch {
  id: string
  name: string
  score: number
  matched_terms: string[]
  naics: { code: string; title: string }[]
  pain_points: string[]
  buyer_types: string[]
  sbir_agencies: string[]
}

export interface MatchResult {
  matched: boolean
  matches: IndustryMatch[]
  message: string
  note: string
  naics_source: string
  sbir_topics_url: string
}

export interface ClarifyQuestion {
  id: 'public' | 'funding' | 'students' | 'outside_interest' | 'course_release' | 'third_party'
  text: string
  why: string
  options: { value: string; label: string }[]
}

export interface ClarifyResult {
  questions: ClarifyQuestion[]
  note: string
}

export interface ChecklistItem {
  id: string
  title: string
  status: 'action' | 'review'
  why: string
  actions: string[]
  links: { label: string; url: string }[]
  citations: PolicyCitation[]
  tool: 'buyout' | null
}

export interface ChecklistResult {
  items: ChecklistItem[]
  disclaimer: string
}

export interface LookupItem {
  kind: 'literature' | 'award'
  title: string
  year: number | null
  source: string
  url: string
  detail: string
}

export interface LookupResult {
  mode: 'fixture' | 'live'
  terms: string[]
  retrieved: string
  items: LookupItem[]
  message: string
  note: string
}

// ---- Advisor contract (frozen on the backend: tests/test_advisor.py::test_contract_is_frozen) ----
export type AdvisorIntent = 'policy' | 'concept' | 'referral' | 'out_of_scope'
export type BlockType = 'policy_quote' | 'glossary' | 'coach' | 'referral'

export interface AdvisorBlock {
  type: BlockType
  source_label: string
  title: string
  body: string
  citations: PolicyCitation[]
  next_questions: string[]
}

export interface AdvisorResponse {
  intent: AdvisorIntent
  blocks: AdvisorBlock[]
}

export interface GlossaryEntry {
  id: string
  term: string
  aliases: string[]
  plain: string
  example: string
  think_about: string[]
  related_fields: string[]
  related: string[]
  reviewed_by: string | null
  reviewed_on: string | null
  source_label: string
}

export type ReadinessDimensionId =
  | 'problem'
  | 'application'
  | 'difference'
  | 'evidence'
  | 'related_work'
  | 'timing'

export interface ReadinessDimension {
  id: ReadinessDimensionId
  status: 'stated' | 'partly' | 'not_found'
  quote: string | null
  follow_up: string | null
  needs_author: boolean
}

export interface ReadinessResult {
  dimensions: ReadinessDimension[]
  note: string
}

export type Answers =Record<string, string>

export interface CommercializationStatus {
  llm_enabled: boolean
  model: string | null
  privacy_note: string
  idf_fields: number
  policy_note: string
}

// Reading a PDF, and Claude when opted in, can take well over the 10 s default.
const SLOW_MS = 90_000

export const commercializationService = {
  async getStatus(): Promise<CommercializationStatus> {
    const res = await apiClient.get<CommercializationStatus>('/commercialization/status')
    return res.data
  },

  async draftFromFile(file: File, useLlm: boolean): Promise<DraftResult> {
    const form = new FormData()
    form.append('file', file)
    form.append('use_llm', String(useLlm))
    const res = await apiClient.post<DraftResult>('/commercialization/idf/draft', form, {
      timeout: SLOW_MS,
      // let the browser set the multipart boundary
      headers: { 'Content-Type': undefined },
    })
    return res.data
  },

  async draftFromText(text: string, useLlm: boolean): Promise<DraftResult> {
    const res = await apiClient.post<DraftResult>(
      '/commercialization/idf/draft-text',
      { text, use_llm: useLlm },
      { timeout: SLOW_MS }
    )
    return res.data
  },

  async askPolicy(question: string): Promise<PolicyAnswer> {
    const res = await apiClient.post<PolicyAnswer>('/commercialization/policy/ask', { question })
    return res.data
  },

  async askAdvisor(question: string): Promise<AdvisorResponse> {
    const res = await apiClient.post<AdvisorResponse>('/commercialization/advisor/ask', { question })
    return res.data
  },

  async glossary(): Promise<GlossaryEntry[]> {
    const res = await apiClient.get<GlossaryEntry[]>('/commercialization/glossary')
    return res.data
  },

  async readiness(
    draft: DraftResult,
    extraText: string,
    coveredElsewhere: ReadinessDimensionId[]
  ): Promise<ReadinessResult> {
    const res = await apiClient.post<ReadinessResult>('/commercialization/readiness', {
      draft,
      extra_text: extraText,
      covered_elsewhere: coveredElsewhere,
    })
    return res.data
  },

  async clarify(draft: DraftResult): Promise<ClarifyResult> {
    const res = await apiClient.post<ClarifyResult>('/commercialization/clarify', draft)
    return res.data
  },

  async checklist(draft: DraftResult, answers: Answers): Promise<ChecklistResult> {
    const res = await apiClient.post<ChecklistResult>('/commercialization/checklist', { draft, answers })
    return res.data
  },

  async lookup(terms: string[]): Promise<LookupResult> {
    const res = await apiClient.post<LookupResult>('/commercialization/lookup', { terms }, { timeout: 30_000 })
    return res.data
  },

  async exportPackage(draft: DraftResult, answers: Answers): Promise<Blob> {
    const res = await apiClient.post<Blob>(
      '/commercialization/export',
      { draft, answers },
      { responseType: 'blob', timeout: SLOW_MS }
    )
    return res.data
  },

  async match(text: string): Promise<MatchResult> {
    const res = await apiClient.post<MatchResult>('/commercialization/match', { text })
    return res.data
  },
}

export const fieldValue = (draft: DraftResult | null, id: string): string =>
  draft?.fields.find((f) => f.id === id)?.value ?? ''

export default commercializationService
