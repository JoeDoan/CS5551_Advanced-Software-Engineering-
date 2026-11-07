import React, { useState } from 'react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  AdvisorBlock,
  AdvisorResponse,
  BlockType,
  commercializationService,
} from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'
import { Citation } from './Citation'

// One of each kind of answer, so a user sees how the advisor behaves: a policy question,
// a definition, and a question it will refer on instead of answering.
const EXAMPLES = [
  'Who owns an invention I make using university resources?',
  'What is prior art?',
  'Do I have to disclose consulting for a company every year?',
  'Is my invention patentable?',
]

const BADGE: Record<BlockType, 'info' | 'neutral' | 'warning' | 'success'> = {
  policy_quote: 'info',
  glossary: 'neutral',
  referral: 'warning',
  coach: 'success',
}

const isDraftLabel = (label: string) => /\bdraft\b/i.test(label)

export const AdvisorBlockView: React.FC<{ block: AdvisorBlock; onAsk: (q: string) => void; busy: boolean }> = ({
  block,
  onAsk,
  busy,
}) => (
  <div
    className={
      block.type === 'referral'
        ? 'border border-amber-300 bg-amber-50/50 rounded-lg p-4 space-y-2'
        : 'border border-slate-200 bg-white rounded-lg p-4 space-y-2'
    }
    data-testid={`block-${block.type}`}
  >
    <div className="flex flex-wrap items-start justify-between gap-2">
      <h3 className="text-sm font-semibold text-slate-800">{block.title}</h3>
      {/* The source label is the honesty mechanism: it says who wrote this text. */}
      <Badge
        variant={block.type === 'glossary' && isDraftLabel(block.source_label) ? 'warning' : BADGE[block.type]}
        data-testid="source-label"
      >
        {block.source_label}
      </Badge>
    </div>
    {block.body
      .split('\n\n')
      .filter(Boolean)
      .map((para, i) => (
        <p key={i} className="text-sm text-slate-700 whitespace-pre-line">
          {para}
        </p>
      ))}
    {block.citations.length > 0 && (
      <div className="space-y-2 pt-1">
        {block.citations.map((c) => (
          <Citation key={c.passage_id} c={c} />
        ))}
      </div>
    )}
    {block.next_questions.length > 0 && (
      <div className="flex flex-wrap gap-2 pt-1" aria-label="Follow-up questions">
        {block.next_questions.map((q) => (
          <button
            key={q}
            type="button"
            disabled={busy}
            className="text-xs px-2 py-1 rounded-full border border-slate-300 text-slate-600 hover:bg-slate-100 disabled:opacity-50"
            onClick={() => onAsk(q)}
            data-testid="chip"
          >
            {q}
          </button>
        ))}
      </div>
    )}
  </div>
)

export const AdvisorBox: React.FC = () => {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<AdvisorResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ask = async (q: string) => {
    const text = q.trim()
    if (text.length < 3) return
    setQuestion(text)
    setBusy(true)
    setError(null)
    try {
      setResponse(await commercializationService.askAdvisor(text))
    } catch (e) {
      setResponse(null)
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Ask the advisor</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Policy answers are quoted word for word from public University of Missouri and UMKC policies, with
            their source and version. Plain-language explanations are written by this project&apos;s team and are
            labelled as drafts until the technology office reviews them. Questions about whether something is
            patentable or novel, who is an inventor, or what to file are referred to the office, not answered.
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
              placeholder="Ask about a policy, a term like novelty or prior art, or how disclosure works"
              aria-label="Your question"
              value={question}
              maxLength={600}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !busy) void ask(question)
              }}
              data-testid="advisor-input"
            />
            <Button onClick={() => ask(question)} disabled={busy || question.trim().length < 3} data-testid="advisor-ask">
              {busy ? 'Looking…' : 'Ask'}
            </Button>
          </div>
          {error && <Alert variant="danger">{error}</Alert>}
        </CardContent>
      </Card>

      {response && (
        <div className="space-y-3" data-testid="advisor-answer" data-intent={response.intent}>
          {response.blocks.map((b, i) => (
            <AdvisorBlockView key={`${b.type}-${i}`} block={b} onAsk={ask} busy={busy} />
          ))}
        </div>
      )}
    </>
  )
}

export default AdvisorBox
