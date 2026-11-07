import React, { useState } from 'react'
import { Alert, Badge, Button, Modal } from '../ui'
import { GlossaryEntry, commercializationService } from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'

export const matchesEntry = (e: GlossaryEntry, query: string): boolean => {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return [e.term, ...e.aliases].some((t) => t.toLowerCase().includes(q))
}

/** A button that opens the plain-language glossary. Entries load when it is first opened. */
export const GlossaryDrawer: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<GlossaryEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const show = async () => {
    setOpen(true)
    if (entries) return
    try {
      setEntries(await commercializationService.glossary())
      setError(null)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  const visible = (entries ?? []).filter((e) => matchesEntry(e, query))

  return (
    <>
      <Button variant="outline" size="sm" onClick={show} data-testid="glossary-open">
        Glossary of terms
      </Button>
      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Glossary of terms"
        description="Plain-language explainers. Not University policy."
        maxWidth="xl"
      >
        <div className="space-y-3" data-testid="glossary-body">
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Search a term"
            aria-label="Search the glossary"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            data-testid="glossary-search"
          />
          {error && <Alert variant="danger">{error}</Alert>}
          {!entries && !error && <p className="text-xs text-slate-500">Loading…</p>}
          {entries && visible.length === 0 && <p className="text-xs text-slate-500">No term matches “{query}”.</p>}
          {visible.map((e) => (
            <div key={e.id} className="border border-slate-200 rounded-lg p-3 space-y-1" data-testid={`glossary-${e.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h4 className="text-sm font-semibold text-slate-800">{e.term}</h4>
                <Badge variant={e.reviewed_by ? 'success' : 'warning'}>{e.source_label}</Badge>
              </div>
              <p className="text-sm text-slate-700">{e.plain}</p>
              <p className="text-xs text-slate-600">Example: {e.example}</p>
              {e.think_about.length > 0 && (
                <ul className="list-disc pl-4 text-xs text-slate-600">
                  {e.think_about.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </Modal>
    </>
  )
}

export default GlossaryDrawer
