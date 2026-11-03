import React, { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  DraftResult,
  LookupResult,
  MatchResult,
  commercializationService,
  fieldValue,
} from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'

const MAX_TERMS = 5
const MAX_WORDS = 3
const MAX_CHARS = 30

// Same rule the server enforces: a short phrase of letters, numbers, spaces and hyphens.
const isBroadTerm = (t: string): boolean =>
  /^[a-z0-9][a-z0-9 -]*$/.test(t) && t.split(/\s+/).length <= MAX_WORDS && t.length <= MAX_CHARS

// Broad domain terms only: short keyword phrases, never the raw title.
export const suggestTerms = (draft: DraftResult | null, match: MatchResult | null): string[] => {
  const fromKeywords = fieldValue(draft, 'A1_keywords')
    .split(/[;,]/)
    .map((t) => t.trim().toLowerCase())
    .filter(isBroadTerm)
  const fromMatch = (match?.matches ?? []).flatMap((m) => m.matched_terms)
  return Array.from(new Set([...fromKeywords, ...fromMatch])).slice(0, MAX_TERMS)
}

export interface ValidateProps {
  draft: DraftResult | null
}

export const Validate: React.FC<ValidateProps> = ({ draft }) => {
  const [match, setMatch] = useState<MatchResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [terms, setTerms] = useState<string[] | null>(null)
  const [draftTerm, setDraftTerm] = useState('')
  const [busy, setBusy] = useState(false)
  const [lookup, setLookup] = useState<LookupResult | null>(null)
  const [lookupError, setLookupError] = useState<string | null>(null)

  const description = useMemo(
    () =>
      ['A1_title', 'A1_general', 'A1_technical', 'A1_novel', 'A1_problem', 'A1_keywords']
        .map((id) => fieldValue(draft, id))
        .filter(Boolean)
        .join('. '),
    [draft]
  )

  useEffect(() => {
    setMatch(null)
    setTerms(null)
    if (description.length < 20) return
    commercializationService
      .match(description)
      .then((m) => {
        setMatch(m)
        setError(null)
      })
      .catch((e) => setError(errorMessage(e)))
  }, [description])

  const shown = terms ?? suggestTerms(draft, match)

  const runLookup = async () => {
    setBusy(true)
    setLookupError(null)
    setLookup(null)
    try {
      setLookup(await commercializationService.lookup(shown))
    } catch (e) {
      setLookupError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const addTerm = () => {
    const t = draftTerm.trim().toLowerCase()
    if (!isBroadTerm(t) || shown.includes(t) || shown.length >= MAX_TERMS) return
    setTerms([...shown, t])
    setDraftTerm('')
  }

  if (!draft) {
    return (
      <Alert variant="info" data-testid="stage-validate">
        Draft your disclosure in step 1 first. The market suggestions are based on it.
      </Alert>
    )
  }

  return (
    <div className="space-y-4" data-testid="stage-validate">
      <Card>
        <CardHeader>
          <CardTitle>Target applications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {error && <Alert variant="danger">{error}</Alert>}
          {match && <Alert variant={match.matched ? 'info' : 'warning'}>{match.message}</Alert>}
          {match?.matches.map((m, i) => (
            <div key={m.id} className="border border-slate-200 rounded-lg p-3 text-sm" data-testid={`market-${m.id}`}>
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-semibold text-slate-800">
                  {i + 1}. {m.name}
                </h3>
                <Badge variant="neutral">Hypothesis</Badge>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Why: your text mentions {m.matched_terms.map((t) => `“${t}”`).join(', ')}
              </p>
              <div className="mt-2 grid md:grid-cols-2 gap-3">
                <div>
                  <p className="text-xs font-semibold text-slate-600">Pain points to test</p>
                  <ul className="list-disc pl-4 text-slate-700">
                    {m.pain_points.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-600">Who might buy</p>
                  <ul className="list-disc pl-4 text-slate-700">
                    {m.buyer_types.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-600">
                NAICS: {m.naics.map((n) => `${n.code} ${n.title}`).join('; ')}
              </p>
              <p className="text-xs text-slate-600">SBIR/STTR agencies: {m.sbir_agencies.join(', ')}</p>
            </div>
          ))}
          {match && (
            <p className="text-xs text-slate-500">
              {match.note}{' '}
              <a className="underline" href={match.sbir_topics_url} target="_blank" rel="noreferrer">
                Open SBIR topics
              </a>
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Prior-art and grant lookup</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Nothing is sent anywhere automatically. Only the broad terms below would be searched, and you can edit
            them first.
          </p>
          <div className="flex flex-wrap gap-2" data-testid="term-pills">
            {shown.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 text-sm text-slate-700"
              >
                {t}
                <button
                  type="button"
                  aria-label={`Remove ${t}`}
                  onClick={() => setTerms(shown.filter((x) => x !== t))}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              placeholder="Add a broad term (up to 3 words)"
              value={draftTerm}
              onChange={(e) => setDraftTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTerm()}
              data-testid="term-input"
            />
            <Button variant="outline" size="sm" onClick={addTerm} disabled={shown.length >= MAX_TERMS}>
              Add
            </Button>
          </div>
          <p className="text-xs text-slate-500" data-testid="will-send">
            Will send: {shown.length ? shown.join(', ') : 'nothing'}
          </p>
          <Button onClick={runLookup} disabled={busy || shown.length === 0} data-testid="lookup-button">
            {busy ? 'Searching…' : 'Run prior-art and grant lookup'}
          </Button>
          {lookupError && <Alert variant="danger">{lookupError}</Alert>}
          {lookup && (
            <div className="space-y-2" data-testid="lookup-result">
              <Alert variant={lookup.mode === 'live' ? 'info' : 'warning'}>
                {lookup.mode === 'live' ? 'Live search. ' : 'Saved results, not a live search. '}
                {lookup.message}
              </Alert>
              {lookup.items.length > 0 && (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      <th className="py-1 pr-2">Type</th>
                      <th className="py-1 pr-2">Title</th>
                      <th className="py-1 pr-2">Year</th>
                      <th className="py-1">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lookup.items.map((i) => (
                      <tr key={i.url + i.title} className="border-t border-slate-100 align-top">
                        <td className="py-1 pr-2 text-slate-600">{i.kind === 'award' ? 'Grant' : 'Paper'}</td>
                        <td className="py-1 pr-2">
                          {i.url ? (
                            <a className="underline text-blue-700" href={i.url} target="_blank" rel="noreferrer">
                              {i.title}
                            </a>
                          ) : (
                            i.title
                          )}
                        </td>
                        <td className="py-1 pr-2 text-slate-600">{i.year ?? ''}</td>
                        <td className="py-1 text-slate-600">
                          {i.source}
                          {i.detail ? `, ${i.detail}` : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <p className="text-xs text-slate-500">{lookup.note}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
