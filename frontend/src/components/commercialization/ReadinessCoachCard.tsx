import React, { useEffect, useRef, useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  DraftResult,
  ReadinessDimension,
  ReadinessDimensionId,
  ReadinessResult,
  ReadinessStatus,
  commercializationService,
  fieldValue,
} from '../../services/commercializationService'

export const READINESS_DIMENSION_LABELS: Record<ReadinessDimensionId, string> = {
  problem: 'Problem being solved',
  application: 'Application or user',
  difference: 'Difference from existing approaches',
  evidence: 'Evidence or development stage',
  related_work: 'Related work and prior art',
  timing: 'Public disclosure and timing',
}

export const READINESS_STATUS_STYLES: Record<
  ReadinessStatus,
  { label: string; badgeClass: string }
> = {
  stated: {
    label: 'stated',
    badgeClass: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  },
  partly: {
    label: 'partly',
    badgeClass: 'bg-amber-50 text-amber-700 border border-amber-200',
  },
  not_found: {
    label: 'not_found',
    badgeClass: 'bg-slate-100 text-slate-700 border border-slate-200',
  },
}

const fieldQuoteOrValue = (draft: DraftResult, id: string): string | null => {
  const found = draft.fields.find((f) => f.id === id)
  const text = (found?.evidence || found?.value || '').trim()
  return text || null
}

const buildFallbackReadiness = (draft: DraftResult, extraText: string): ReadinessResult => {
  const problemQuote = fieldQuoteOrValue(draft, 'A1_problem')
  const appQuote =
    fieldQuoteOrValue(draft, 'A1_general') || fieldQuoteOrValue(draft, 'A1_novel')
  const hasAppCue =
    /\b(user|users|operator|clinician|inspector|engineer|nurse|manager|department|hospital|clinic|depot|plant)\b/i.test(
      `${extraText} ${appQuote ?? ''} ${problemQuote ?? ''}`
    )
  const diffQuote =
    fieldQuoteOrValue(draft, 'A1_different') || fieldQuoteOrValue(draft, 'D1_competition')
  const evidenceText = `${extraText} ${fieldValue(draft, 'A1_general')}`.trim()
  const hasEvidenceCue = /\b(tested|measured|results|prototype|validated|experiment|bench)\b/i.test(
    evidenceText
  )
  const priorArtQuote = fieldQuoteOrValue(draft, 'D1_prior_art')
  const timingQuote =
    fieldQuoteOrValue(draft, 'A2_first_public') || fieldQuoteOrValue(draft, 'A3_disclosures')
  const deadlineFlag = draft.flags.find(
    (fl) => fl.level === 'deadline' || fl.level === 'warning'
  )

  const dimensions: ReadinessDimension[] = [
    {
      id: 'problem',
      status: problemQuote ? 'stated' : 'not_found',
      quote: problemQuote,
      follow_up: problemQuote
        ? null
        : 'What concrete problem or bottleneck does this work address?',
      needs_author: !problemQuote,
    },
    {
      id: 'application',
      status: hasAppCue ? 'stated' : appQuote ? 'partly' : 'not_found',
      quote: appQuote,
      follow_up: hasAppCue
        ? null
        : 'Who is the specific user or operator, and what changes in their workflow?',
      needs_author: !hasAppCue,
    },
    {
      id: 'difference',
      status: diffQuote ? 'stated' : 'not_found',
      quote: diffQuote,
      follow_up: diffQuote
        ? null
        : 'How does this differ from current practice or competing methods?',
      needs_author: !diffQuote,
    },
    {
      id: 'evidence',
      status: hasEvidenceCue ? 'stated' : 'not_found',
      quote: hasEvidenceCue ? fieldQuoteOrValue(draft, 'A1_general') : null,
      follow_up: hasEvidenceCue
        ? null
        : 'What data, simulation, or prototype results exist so far?',
      needs_author: !hasEvidenceCue,
    },
    {
      id: 'related_work',
      status: priorArtQuote ? 'partly' : 'not_found',
      quote: priorArtQuote,
      follow_up: 'Which closest papers, patents, or existing tools should the office compare against?',
      needs_author: true,
    },
    {
      id: 'timing',
      status: timingQuote ? 'stated' : deadlineFlag ? 'partly' : 'not_found',
      quote: timingQuote ?? deadlineFlag?.message ?? null,
      follow_up: timingQuote
        ? null
        : 'Are any talks, posters, preprints, or theses planned in the next 3 to 6 months?',
      needs_author: !timingQuote,
    },
  ]

  return {
    dimensions,
    note: 'No score and no verdict. This lists what the disclosure does not yet say.',
  }
}

export interface ReadinessCoachCardProps {
  draft: DraftResult
}

export const ReadinessCoachCard: React.FC<ReadinessCoachCardProps> = ({ draft }) => {
  const [readiness, setReadiness] = useState<ReadinessResult | null>(() =>
    buildFallbackReadiness(draft, '')
  )
  const [extraText, setExtraText] = useState('')
  const [coveredElsewhere, setCoveredElsewhere] = useState<Record<string, boolean>>({})
  const [busy, setBusy] = useState(false)
  const reqIdRef = useRef(0)

  const loadReadiness = async (currentDraft: DraftResult, extra: string) => {
    const reqId = ++reqIdRef.current
    setBusy(true)
    try {
      const res = await commercializationService.getReadiness(currentDraft, extra)
      if (reqId !== reqIdRef.current) return
      if (res && Array.isArray(res.dimensions)) {
        setReadiness(res)
      } else {
        setReadiness(buildFallbackReadiness(currentDraft, extra))
      }
    } catch {
      if (reqId !== reqIdRef.current) return
      setReadiness(buildFallbackReadiness(currentDraft, extra))
    } finally {
      if (reqId === reqIdRef.current) {
        setBusy(false)
      }
    }
  }

  useEffect(() => {
    setExtraText('')
    setCoveredElsewhere({})
    void loadReadiness(draft, '')
    return () => {
      reqIdRef.current += 1
    }
  }, [draft])

  return (
    <Card data-testid="readiness-coach-card">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Disclosure readiness coach</CardTitle>
          <Badge variant="info" data-testid="readiness-source-badge">
            From your draft
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-slate-600">
          {readiness?.note ??
            'No score and no verdict. This lists what the disclosure does not yet say.'}
        </p>

        {readiness && (
          <div className="space-y-3">
            {readiness.dimensions.map((dim) => {
              const style = READINESS_STATUS_STYLES[dim.status] ?? READINESS_STATUS_STYLES.not_found
              const isCovered = Boolean(coveredElsewhere[dim.id])
              return (
                <div
                  key={dim.id}
                  className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5"
                  data-testid={`readiness-dim-${dim.id}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-800">
                      {READINESS_DIMENSION_LABELS[dim.id] ?? dim.id}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${style.badgeClass}`}
                        data-testid={`readiness-status-${dim.id}`}
                      >
                        {style.label}
                      </span>
                      {dim.status !== 'stated' && (
                        <label className="flex items-center gap-1 text-xs text-slate-500 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isCovered}
                            onChange={(e) =>
                              setCoveredElsewhere((prev) => ({
                                ...prev,
                                [dim.id]: e.target.checked,
                              }))
                            }
                            data-testid={`readiness-covered-${dim.id}`}
                          />
                          Covered elsewhere
                        </label>
                      )}
                    </div>
                  </div>

                  {dim.quote && (
                    <p className="text-xs text-slate-600 italic">
                      From your draft: “{dim.quote}”
                    </p>
                  )}

                  {dim.status !== 'stated' && dim.follow_up && !isCovered && (
                    <p className="text-sm text-slate-800">{dim.follow_up}</p>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <div className="border-t border-slate-200 pt-3 space-y-2">
          <label
            htmlFor="readiness-extra-input"
            className="block text-xs font-medium text-slate-700"
          >
            In one or two sentences, who would use this and what changes for them? Not stored.
          </label>
          <div className="flex gap-2">
            <input
              id="readiness-extra-input"
              type="text"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Anything else about the stage, prototype test results, or target user (not stored)"
              value={extraText}
              onChange={(e) => setExtraText(e.target.value)}
              data-testid="readiness-extra-input"
            />
            <Button
              type="button"
              onClick={() => void loadReadiness(draft, extraText)}
              disabled={busy}
              data-testid="readiness-update-button"
            >
              {busy ? 'Updating…' : 'Update coach'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default ReadinessCoachCard
