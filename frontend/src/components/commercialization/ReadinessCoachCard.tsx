import React, { useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  DraftResult,
  ReadinessDimension,
  ReadinessDimensionId,
  ReadinessResult,
  commercializationService,
} from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'

export const MAX_EXTRA = 1500

export const TITLES: Record<ReadinessDimensionId, string> = {
  problem: 'Problem',
  application: 'Application or user',
  difference: 'Difference from others',
  evidence: 'Evidence or stage',
  related_work: 'Related work',
  timing: 'Timing',
}

const STATUS: Record<ReadinessDimension['status'], { label: string; variant: 'success' | 'warning' | 'neutral' }> = {
  stated: { label: 'Stated in your text', variant: 'success' },
  partly: { label: 'Partly stated', variant: 'warning' },
  // Neutral on purpose: "not found" means the text does not say it, not that the work lacks it.
  not_found: { label: 'Not found in your text', variant: 'neutral' },
}

export interface ReadinessCoachCardProps {
  draft: DraftResult
}

export const ReadinessCoachCard: React.FC<ReadinessCoachCardProps> = ({ draft }) => {
  const [result, setResult] = useState<ReadinessResult | null>(null)
  const [extra, setExtra] = useState('')
  const [appliedExtra, setAppliedExtra] = useState('')
  const [covered, setCovered] = useState<ReadinessDimensionId[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // A new draft starts over. Keep the same array when it is already empty, so mounting does not
  // trigger a second request.
  useEffect(() => {
    setExtra('')
    setAppliedExtra('')
    setCovered((c) => (c.length ? [] : c))
  }, [draft])

  useEffect(() => {
    let current = true
    setBusy(true)
    commercializationService
      .readiness(draft, appliedExtra, covered)
      .then((r) => {
        if (!current) return
        setResult(r)
        setError(null)
      })
      .catch((e) => current && setError(errorMessage(e)))
      .finally(() => current && setBusy(false))
    return () => {
      current = false
    }
  }, [draft, appliedExtra, covered])

  const toggleCovered = (id: ReadinessDimensionId) =>
    setCovered((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]))

  return (
    <Card data-testid="readiness-card">
      <CardHeader>
        <CardTitle>What your disclosure does not say yet</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          Six things reviewers and partners usually look for. This reads your own text, quotes what it finds and asks
          one question per gap. It does not score your work or judge whether it is ready.
        </p>
        {error && <Alert variant="danger">{error}</Alert>}

        {result?.dimensions.map((d) => {
          const marked = covered.includes(d.id)
          const s = STATUS[d.status]
          return (
            <div key={d.id} className="border border-slate-200 rounded-lg p-3 space-y-1" data-testid={`dimension-${d.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-800">{TITLES[d.id]}</h3>
                <div className="flex gap-2">
                  {d.needs_author && !marked && <Badge variant="info">Needs your confirmation</Badge>}
                  <Badge variant={s.variant}>{s.label}</Badge>
                </div>
              </div>
              {d.quote && <p className="text-sm text-slate-700">From your text: “{d.quote}”</p>}
              {d.follow_up && <p className="text-sm text-slate-800 font-medium">{d.follow_up}</p>}
              {marked && <p className="text-xs text-slate-500">You marked this as covered elsewhere.</p>}
              {d.status !== 'stated' && (
                <label className="flex items-center gap-1 text-xs text-slate-600 pt-1">
                  <input type="checkbox" checked={marked} onChange={() => toggleCovered(d.id)} />
                  Covered elsewhere (for example in the form itself)
                </label>
              )}
            </div>
          )
        })}

        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-800" htmlFor="readiness-extra">
            Anything else about the stage or the application?
          </label>
          <textarea
            id="readiness-extra"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            rows={3}
            maxLength={MAX_EXTRA}
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            data-testid="readiness-extra"
          />
          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="outline"
              disabled={busy || extra === appliedExtra}
              onClick={() => setAppliedExtra(extra)}
              data-testid="readiness-update"
            >
              {busy ? 'Reading…' : 'Update with this text'}
            </Button>
            <span className="text-xs text-slate-500">
              Sent with the request to read it, then discarded. It is not saved.
            </span>
          </div>
        </div>

        {result && <p className="text-xs text-slate-500">{result.note}</p>}
      </CardContent>
    </Card>
  )
}

export default ReadinessCoachCard
