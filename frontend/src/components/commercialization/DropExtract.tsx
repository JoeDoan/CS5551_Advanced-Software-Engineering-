import React, { useRef, useState } from 'react'
import { FileUp } from 'lucide-react'
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  CommercializationStatus,
  DraftField,
  DraftResult,
  FieldStatus,
  commercializationService,
} from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'

const STATUS_BADGE: Record<FieldStatus, { label: string; variant: 'success' | 'warning' | 'neutral' }> = {
  proposed: { label: 'Proposed', variant: 'success' },
  needs_author: { label: 'Please confirm', variant: 'warning' },
  blank: { label: 'Yours to fill', variant: 'neutral' },
}

const FLAG_VARIANT = { info: 'info', warning: 'warning', deadline: 'danger' } as const

export interface DropExtractProps {
  status: CommercializationStatus | null
  draft: DraftResult | null
  onDraft: (draft: DraftResult) => void
}

const groupBySection = (fields: DraftField[]) => {
  const groups = new Map<string, DraftField[]>()
  fields.forEach((f) => {
    const key = f.section.split('.')[0]
    groups.set(key, [...(groups.get(key) ?? []), f])
  })
  return Array.from(groups.entries())
}

const SECTION_TITLES: Record<string, string> = {
  A: 'A. Invention information',
  B: 'B. External support',
  C: 'C. Potential inventors',
  D: 'D. Commercial potential',
  E: 'E. Signature',
}

export const DropExtract: React.FC<DropExtractProps> = ({ status, draft, onDraft }) => {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [pasted, setPasted] = useState('')
  const [useLlm, setUseLlm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      const result = file
        ? await commercializationService.draftFromFile(file, useLlm)
        : await commercializationService.draftFromText(pasted, useLlm)
      onDraft(result)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const canRun = !busy && (file !== null || pasted.trim().length > 0)

  return (
    <div className="space-y-4" data-testid="stage-drop">
      <Card>
        <CardHeader>
          <CardTitle>Drop your paper, proposal or lab summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            {status?.privacy_note ??
              'Your document is processed in memory and is not saved. By default the text stays on this server.'}
          </p>

          <div
            className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center bg-slate-50"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              const dropped = e.dataTransfer.files?.[0]
              if (dropped) setFile(dropped)
            }}
          >
            <FileUp className="w-6 h-6 mx-auto text-slate-400" />
            <p className="text-sm text-slate-700 mt-2">
              {file ? file.name : 'Drag a PDF here, or choose a file'}
            </p>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              data-testid="file-input"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <Button variant="outline" size="sm" className="mt-3" onClick={() => inputRef.current?.click()}>
              Choose PDF
            </Button>
          </div>

          <label className="block text-sm font-medium text-slate-700">
            Or paste text instead
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm min-h-[90px]"
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              data-testid="paste-input"
              disabled={file !== null}
            />
          </label>

          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={useLlm}
              disabled={!status?.llm_enabled}
              onChange={(e) => setUseLlm(e.target.checked)}
              data-testid="use-llm"
              className="mt-1"
            />
            <span>
              Use Claude for a better draft.{' '}
              <strong>This sends your document text to Anthropic's API.</strong>{' '}
              {!status?.llm_enabled && '(Claude is not configured on this server.)'}
            </span>
          </label>

          <div className="flex gap-2">
            <Button onClick={run} disabled={!canRun} data-testid="draft-button">
              {busy ? 'Reading…' : 'Draft my disclosure'}
            </Button>
            {file && (
              <Button variant="ghost" onClick={() => setFile(null)}>
                Remove file
              </Button>
            )}
          </div>
          {error && <Alert variant="danger">{error}</Alert>}
        </CardContent>
      </Card>

      {draft && (
        <Card data-testid="draft-result">
          <CardHeader>
            <CardTitle>
              Draft disclosure ({draft.extractor === 'claude' ? 'Claude' : 'offline extractor'})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="success">{draft.counts.proposed} proposed</Badge>
              <Badge variant="warning">{draft.counts.needs_author} to confirm</Badge>
              <Badge variant="neutral">{draft.counts.blank} left to you</Badge>
              <span className="text-slate-500 self-center">
                {draft.pages_read ? `${draft.pages_read} page(s), ` : ''}
                {draft.chars_read.toLocaleString()} characters read
              </span>
            </div>

            {draft.flags.map((f, i) => (
              <Alert key={i} variant={FLAG_VARIANT[f.level]}>
                {f.message}
              </Alert>
            ))}
            {draft.warnings.map((w, i) => (
              <Alert key={`w${i}`} variant="warning">
                {w}
              </Alert>
            ))}

            {groupBySection(draft.fields).map(([key, fields]) => (
              <div key={key}>
                <h3 className="text-sm font-semibold text-slate-800 mb-2">{SECTION_TITLES[key] ?? key}</h3>
                <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
                  {fields.map((f) => {
                    const badge = STATUS_BADGE[f.status]
                    return (
                      <div key={f.id} className="p-3 text-sm" data-testid={`field-${f.id}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="font-medium text-slate-800">
                            <span className="text-slate-400 mr-1">{f.section}</span>
                            {f.label}
                          </div>
                          <Badge variant={badge.variant}>{badge.label}</Badge>
                        </div>
                        {f.value ? (
                          <>
                            <p className="mt-1 text-slate-700">{f.value}</p>
                            <p className="mt-1 text-xs text-slate-500 italic">From your document: “{f.evidence}”</p>
                          </>
                        ) : null}
                        {f.note && <p className="mt-1 text-xs text-slate-500">{f.note}</p>}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}

            <p className="text-xs text-slate-500">
              Official form:{' '}
              <a className="underline" href={draft.form_url}>
                UM-16C Invention Disclosure Form
              </a>
              . Return it to: {draft.returns_to}. This is a draft for you to verify, not legal advice.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
