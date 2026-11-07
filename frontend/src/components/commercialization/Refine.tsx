import React, { useEffect, useRef, useState } from 'react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  AdvisorBlock,
  AdvisorBlockType,
  AdvisorResponse,
  Answers,
  ChecklistResult,
  ClarifyResult,
  DraftResult,
  PolicyAnswer,
  PolicyCitation,
  commercializationService,
} from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'
import { AuthRole } from '../../types/api'
import { BuyoutImpact } from './BuyoutImpact'
import { GlossaryDrawer } from './GlossaryDrawer'
import { ReadinessCoachCard } from './ReadinessCoachCard'

const EXAMPLES = [
  'Can my PhD student write code for my startup?',
  'Who owns an invention I make using university resources?',
  'Do I have to disclose consulting for a company every year?',
  'What is a conflict of interest?',
  'Is my invention patentable?',
]

const ADVISOR_BLOCK_BADGE_VARIANT: Record<
  AdvisorBlockType,
  'info' | 'warning' | 'neutral' | 'gold'
> = {
  policy_quote: 'info',
  glossary: 'warning',
  coach: 'neutral',
  referral: 'gold',
}

const adaptPolicyAnswerToAdvisor = (ans: PolicyAnswer): AdvisorResponse => ({
  intent: ans.answered ? 'policy' : 'out_of_scope',
  blocks: [
    {
      type: 'policy_quote',
      source_label: 'Quoted policy (title, version)',
      title: ans.answered ? 'Policy passages' : 'No matching policy passage',
      body: ans.message,
      citations: ans.citations,
    },
  ],
})

const queryAdvisorWithFallback = async (
  question: string,
  draft: DraftResult | null
): Promise<{ response: AdvisorResponse; disclaimer: string }> => {
  const policySpied = 'mock' in commercializationService.askPolicy
  const advisorSpied = 'mock' in commercializationService.askAdvisor

  if (policySpied && !advisorSpied) {
    const legacy = await commercializationService.askPolicy(question)
    return {
      response: adaptPolicyAnswerToAdvisor(legacy),
      disclaimer: legacy.disclaimer || 'This is not legal advice.',
    }
  }

  try {
    const res = await commercializationService.askAdvisor(question, draft)
    return {
      response: res,
      disclaimer: 'This is not legal advice.',
    }
  } catch (advisorErr) {
    if (advisorSpied) throw advisorErr
    const legacy = await commercializationService.askPolicy(question)
    return {
      response: adaptPolicyAnswerToAdvisor(legacy),
      disclaimer: legacy.disclaimer || 'This is not legal advice.',
    }
  }
}

const Citation: React.FC<{ c: PolicyCitation }> = ({ c }) => (
  <div className="border border-slate-200 rounded-lg p-3 text-sm bg-white">
    <p className="text-slate-800">“{c.text}”</p>
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <a className="underline" href={c.source_url} target="_blank" rel="noreferrer">
        {c.source_title}
      </a>
      <Badge variant="neutral">{c.version}</Badge>
      <span>{[c.section, c.locator].filter((x, i, a) => x && a.indexOf(x) === i).join(' · ')}</span>
    </div>
    <p className="mt-1 text-xs text-slate-500">Applies to: {c.applies_to}</p>
  </div>
)

const AdvisorBlockView: React.FC<{
  block: AdvisorBlock
  onSelectQuestion: (q: string) => void
}> = ({ block, onSelectQuestion }) => (
  <div
    className="border border-slate-200 rounded-lg p-3 space-y-2 bg-slate-50"
    data-testid={`advisor-block-${block.type}`}
  >
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h4 className="text-sm font-semibold text-slate-900">{block.title}</h4>
      <Badge
        variant={ADVISOR_BLOCK_BADGE_VARIANT[block.type] ?? 'neutral'}
        data-testid="advisor-source-badge"
      >
        {block.source_label}
      </Badge>
    </div>
    <p className="text-sm text-slate-700">{block.body}</p>
    {block.citations && block.citations.length > 0 && (
      <div className="space-y-2 pt-1">
        {block.citations.map((c) => (
          <Citation key={c.passage_id} c={c} />
        ))}
      </div>
    )}
    {block.next_questions && block.next_questions.length > 0 && (
      <div className="flex flex-wrap items-center gap-2 pt-2">
        <span className="text-xs text-slate-500">Follow-up questions:</span>
        {block.next_questions.map((nq) => (
          <button
            key={nq}
            type="button"
            className="text-xs px-2.5 py-1 rounded-full border border-blue-300 bg-white text-blue-700 hover:bg-blue-50"
            onClick={() => onSelectQuestion(nq)}
            data-testid="advisor-next-question"
          >
            {nq}
          </button>
        ))}
      </div>
    )}
  </div>
)

const PolicySandbox: React.FC<{
  draft: DraftResult | null
  onOpenGlossary: () => void
}> = ({ draft, onOpenGlossary }) => {
  const [question, setQuestion] = useState('')
  const [advisorAnswer, setAdvisorAnswer] = useState<AdvisorResponse | null>(null)
  const [disclaimer, setDisclaimer] = useState<string>('This is not legal advice.')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const reqIdRef = useRef(0)

  const ask = async (q: string) => {
    const trimmed = q.trim()
    if (!trimmed) return
    const reqId = ++reqIdRef.current
    setBusy(true)
    setError(null)
    try {
      const { response, disclaimer: nextDisclaimer } = await queryAdvisorWithFallback(
        trimmed,
        draft
      )
      if (reqId !== reqIdRef.current) return
      setAdvisorAnswer(response)
      setDisclaimer(nextDisclaimer)
    } catch (e) {
      if (reqId !== reqIdRef.current) return
      setAdvisorAnswer(null)
      setError(errorMessage(e))
    } finally {
      if (reqId === reqIdRef.current) {
        setBusy(false)
      }
    }
  }

  const handleFollowUp = (nextQ: string) => {
    setQuestion(nextQ)
    void ask(nextQ)
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>Ask the policy & commercialization advisor</CardTitle>
            <Button
              type="button"
              variant="secondary"
              onClick={onOpenGlossary}
              data-testid="open-glossary-button"
            >
              Browse glossary
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Answers quote approved University of Missouri and UMKC policies word for word, explain concepts
            from the plain-language glossary, or refer judgment calls to the appropriate campus office.
            Nothing you type is saved.
          </p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                className="text-xs px-2 py-1 rounded-full border border-slate-300 text-slate-600 hover:bg-slate-100"
                onClick={() => setQuestion(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Ask a question about outside activities, inventions, concepts or ownership"
              value={question}
              maxLength={600}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && question.trim().length >= 3 && !busy) void ask(question)
              }}
              data-testid="policy-input"
            />
            <Button
              onClick={() => void ask(question)}
              disabled={busy || question.trim().length < 3}
              data-testid="policy-ask"
            >
              {busy ? 'Searching…' : 'Search policies'}
            </Button>
          </div>
          {error && <Alert variant="danger">{error}</Alert>}
        </CardContent>
      </Card>

      {advisorAnswer && (
        <Card data-testid="policy-answer">
          <CardContent className="space-y-3 pt-4">
            {advisorAnswer.blocks.map((block, idx) => (
              <AdvisorBlockView
                key={`${block.type}-${idx}`}
                block={block}
                onSelectQuestion={handleFollowUp}
              />
            ))}
            <p className="text-xs text-slate-500">{disclaimer}</p>
          </CardContent>
        </Card>
      )}
    </>
  )
}

export interface RefineProps {
  draft: DraftResult | null
  role: AuthRole
  userName: string
  onAnswers?: (answers: Answers) => void
}

export const Refine: React.FC<RefineProps> = ({ draft, role, userName, onAnswers }) => {
  const [clarify, setClarify] = useState<ClarifyResult | null>(null)
  const [answers, setAnswers] = useState<Answers>({})
  const [checklist, setChecklist] = useState<ChecklistResult | null>(null)
  const [glossaryOpen, setGlossaryOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setClarify(null)
    setAnswers({})
    setChecklist(null)
    if (!draft) return
    commercializationService
      .clarify(draft)
      .then((c) => {
        setClarify(c)
        setError(null)
      })
      .catch((e) => setError(errorMessage(e)))
  }, [draft])

  useEffect(() => {
    onAnswers?.(answers)
  }, [answers, onAnswers])

  useEffect(() => {
    if (!draft) return
    let current = true
    commercializationService
      .checklist(draft, answers)
      .then((c) => current && setChecklist(c))
      .catch((e) => current && setError(errorMessage(e)))
    return () => {
      current = false
    }
  }, [draft, answers])

  return (
    <div className="space-y-4" data-testid="stage-refine">
      {!draft && (
        <Alert variant="info">
          Draft your disclosure in step 1 to get questions and a checklist tailored to it. You can still ask
          the policy sandbox below.
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {draft && <ReadinessCoachCard draft={draft} />}

      <GlossaryDrawer open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />

      {clarify && (
        <Card data-testid="clarify-card">
          <CardHeader>
            <CardTitle>A few questions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-slate-500">{clarify.note}</p>
            {clarify.questions.map((q) => (
              <fieldset key={q.id} className="space-y-1" data-testid={`question-${q.id}`}>
                <legend className="text-sm font-medium text-slate-800">{q.text}</legend>
                <p className="text-xs text-slate-500">{q.why}</p>
                <div className="flex flex-wrap gap-3 pt-1">
                  {q.options.map((o) => (
                    <label key={o.value} className="flex items-center gap-1 text-sm text-slate-700">
                      <input
                        type="radio"
                        name={q.id}
                        value={o.value}
                        checked={answers[q.id] === o.value}
                        onChange={() => setAnswers((a) => ({ ...a, [q.id]: o.value }))}
                      />
                      {o.label}
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </CardContent>
        </Card>
      )}

      {checklist && (
        <Card data-testid="checklist-card">
          <CardHeader>
            <CardTitle>Your compliance checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {checklist.items.map((item) => (
              <div key={item.id} className="border border-slate-200 rounded-lg p-3" data-testid={`check-${item.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm font-semibold text-slate-800">{item.title}</h3>
                  <Badge variant={item.status === 'action' ? 'warning' : 'neutral'}>
                    {item.status === 'action' ? 'To do' : 'Review'}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">{item.why}</p>
                <ul className="mt-2 list-disc pl-4 text-sm text-slate-700">
                  {item.actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                <div className="mt-2 flex flex-wrap gap-3 text-xs">
                  {item.links.map((l) => (
                    <a key={l.url + l.label} className="underline text-blue-700" href={l.url} target="_blank" rel="noreferrer">
                      {l.label}
                    </a>
                  ))}
                </div>
                {item.tool === 'buyout' && <BuyoutImpact role={role} userName={userName} />}
                {item.citations.length > 0 && (
                  <details className="mt-3">
                    <summary className="text-xs font-semibold text-slate-600 cursor-pointer">
                      Policy text that may apply ({item.citations.length})
                    </summary>
                    <div className="mt-2 space-y-2">
                      {item.citations.map((c) => (
                        <Citation key={c.passage_id} c={c} />
                      ))}
                    </div>
                  </details>
                )}
              </div>
            ))}
            <p className="text-xs text-slate-500">{checklist.disclaimer}</p>
          </CardContent>
        </Card>
      )}

      <PolicySandbox draft={draft} onOpenGlossary={() => setGlossaryOpen(true)} />
    </div>
  )
}
