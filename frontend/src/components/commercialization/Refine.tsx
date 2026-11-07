import React, { useEffect, useState } from 'react'
import { Alert, Badge, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  Answers,
  ChecklistResult,
  ClarifyResult,
  DraftResult,
  commercializationService,
} from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'
import { AuthRole } from '../../types/api'
import { AdvisorBox } from './AdvisorBox'
import { BuyoutImpact } from './BuyoutImpact'
import { Citation } from './Citation'
import { GlossaryDrawer } from './GlossaryDrawer'
import { ReadinessCoachCard } from './ReadinessCoachCard'

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
      <div className="flex justify-end">
        <GlossaryDrawer />
      </div>
      {!draft && (
        <Alert variant="info">
          Draft your disclosure in step 1 to get questions, a checklist and a read of what it does not say yet,
          tailored to it. You can still ask the advisor below.
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {draft && <ReadinessCoachCard draft={draft} />}

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

      <AdvisorBox />
    </div>
  )
}
