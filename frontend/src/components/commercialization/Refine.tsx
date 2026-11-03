import React, { useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
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

const EXAMPLES = [
  'Can my PhD student write code for my startup?',
  'Who owns an invention I make using university resources?',
  'Do I have to disclose consulting for a company every year?',
]

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

const PolicySandbox: React.FC = () => {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<PolicyAnswer | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ask = async (q: string) => {
    setBusy(true)
    setError(null)
    try {
      setAnswer(await commercializationService.askPolicy(q.trim()))
    } catch (e) {
      setAnswer(null)
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Ask the policy sandbox</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Answers are quoted word for word from public University of Missouri and UMKC policies, with their
            source and version. Nothing is paraphrased or generated, and nothing you type is saved.
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
              placeholder="Ask a question about outside activities, inventions or ownership"
              value={question}
              maxLength={600}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && question.trim().length >= 3 && !busy) void ask(question)
              }}
              data-testid="policy-input"
            />
            <Button
              onClick={() => ask(question)}
              disabled={busy || question.trim().length < 3}
              data-testid="policy-ask"
            >
              {busy ? 'Searching…' : 'Search policies'}
            </Button>
          </div>
          {error && <Alert variant="danger">{error}</Alert>}
        </CardContent>
      </Card>

      {answer && (
        <Card data-testid="policy-answer">
          <CardContent className="space-y-3 pt-4">
            <Alert variant={answer.answered ? 'info' : 'warning'}>{answer.message}</Alert>
            {answer.citations.map((c) => (
              <Citation key={c.passage_id} c={c} />
            ))}
            <p className="text-xs text-slate-500">{answer.disclaimer}</p>
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

      <PolicySandbox />
    </div>
  )
}
