import React, { useEffect, useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import {
  GlossaryEntry,
  commercializationService,
} from '../../services/commercializationService'

export const GLOSSARY_SOURCE_LABEL =
  'General explainer, draft, not yet reviewed by the technology office'

export const FALLBACK_GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    term: 'Novelty',
    plain:
      'What is new in your work compared with everything already made public before a filing date.',
    example:
      'An acoustic sensor setup that isolates micro-crack frequencies not separated in earlier bridge studies.',
    what_office_asks:
      'What specific step, structure, or algorithm has not been described in any paper, talk, or code release?',
    related_fields: ['A1_novel', 'A1_different'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Prior art',
    plain:
      'Any public paper, patent, presentation, website, thesis, or open-source repository that existed before filing, including your own.',
    example:
      'A 2023 IEEE conference paper by another lab or your own preprint posted on arXiv last month.',
    what_office_asks:
      'Which 2 to 4 closest papers, patents, or tools would a reviewer compare your work against?',
    related_fields: ['D1_prior_art', 'A2_first_public'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Inventorship',
    plain:
      'A legal determination of who contributed to the conception of at least one patent claim, which differs from academic authorship.',
    example:
      'A PhD student who designed the core signal filter may be an inventor, whereas someone who only ran standard assays may be an author but not an inventor.',
    what_office_asks:
      'Who contributed to conceiving the technical solution, and what was each person’s role and affiliation?',
    related_fields: ['C1_inventors', 'E_submitter'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Public disclosure',
    plain:
      'Any non-confidential communication that enables someone in the field to understand or reproduce the invention.',
    example:
      'Conference slides, poster sessions, published abstracts, thesis defenses open to the public, or public GitHub commits.',
    what_office_asks:
      'When was or will the work first be shared outside the university, and in what format?',
    related_fields: ['A2_first_public', 'A3_disclosures'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Development stage',
    plain:
      'How far the work has progressed from an initial concept or simulation to benchtop data, prototype, or field validation.',
    example:
      'Validated on 12 laboratory concrete beams with repeatable signal-to-noise improvement.',
    what_office_asks:
      'What experimental data, working code, or physical test results exist today?',
    related_fields: ['A1_general', 'A1_limits'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Translational readiness',
    plain:
      'How clearly the research connects to a practical use case, identifiable adopter, and next validation step.',
    example:
      'Knowing that state bridge inspectors need a portable unit that runs in under 10 minutes per span.',
    what_office_asks:
      'What is the next concrete milestone needed before an external partner or SBIR reviewer would test this?',
    related_fields: ['A1_problem', 'A1_general'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Potential application',
    plain:
      'The real-world workflow, product, or service where the invention solves a problem for a specific user.',
    example:
      'Emergency department triage software for prioritizing chest CT scans with suspected pulmonary embolism.',
    what_office_asks:
      'Who would use this in practice, and what decision or workflow changes for them?',
    related_fields: ['A1_problem', 'A1_general'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Differentiation',
    plain:
      'Why a user or licensee would choose this approach over current practice or competing alternatives.',
    example:
      'Uses $200 off-the-shelf transducers instead of $15,000 laser vibrometers while keeping comparable sensitivity.',
    what_office_asks:
      'What are people using today instead, and what measurable advantage does your approach offer?',
    related_fields: ['A1_different', 'D1_competition'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Conflict of interest',
    plain:
      'A situation where an employee’s outside financial interest, consulting, or company role could affect or appear to affect university duties or research objectivity.',
    example:
      'Holding equity in or consulting for a startup that sponsors research in your UMKC laboratory.',
    what_office_asks:
      'Is your annual outside-interest disclosure current, and does any company overlap with your lab, students, or grants?',
    related_fields: ['B1_types', 'C1_inventors'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Invention disclosure',
    plain:
      'A confidential internal report to the university technology office describing a new research result so the office can evaluate protection and licensing options.',
    example:
      'Submitting the UM Invention Disclosure Form before a conference manuscript goes live.',
    what_office_asks:
      'What did you build or discover, who funded it, who contributed, and are any public deadlines approaching?',
    related_fields: ['A1_title', 'A1_general', 'B1_types'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Licence',
    plain:
      'An agreement in which the university grants a company or startup permission to practice university-owned intellectual property under defined terms.',
    example:
      'An exclusive or non-exclusive licence allowing a startup or industry partner to commercialize a patented sensor.',
    what_office_asks:
      'Are any external companies already expressing interest, or is open-source / non-exclusive distribution planned?',
    related_fields: ['D2_licensees', 'B2_agreements'],
    reviewed_by: null,
    reviewed_on: null,
  },
  {
    term: 'Equity',
    plain:
      'Ownership shares or options in an outside company or faculty startup, which trigger conflict-of-interest review when connected to university research or licensing.',
    example:
      'Founding shares in a spinout company seeking an option or licence to intellectual property developed in your lab.',
    what_office_asks:
      'Do any contributors hold or plan to hold ownership or board roles in an entity related to this work?',
    related_fields: ['C1_inventors', 'D2_licensees'],
    reviewed_by: null,
    reviewed_on: null,
  },
]

export interface GlossaryDrawerProps {
  open: boolean
  onClose: () => void
  initialTerm?: string
}

export const GlossaryDrawer: React.FC<GlossaryDrawerProps> = ({
  open,
  onClose,
  initialTerm = '',
}) => {
  const [entries, setEntries] = useState<GlossaryEntry[]>(FALLBACK_GLOSSARY_ENTRIES)
  const [sourceLabel, setSourceLabel] = useState<string>(GLOSSARY_SOURCE_LABEL)
  const [search, setSearch] = useState<string>(initialTerm)

  useEffect(() => {
    if (open) {
      setSearch(initialTerm)
    }
  }, [open, initialTerm])

  useEffect(() => {
    if (!open) return
    let active = true
    commercializationService
      .getGlossary()
      .then((res) => {
        if (!active) return
        if (res && Array.isArray(res.entries) && res.entries.length > 0) {
          setEntries(res.entries)
        } else {
          setEntries(FALLBACK_GLOSSARY_ENTRIES)
        }
        setSourceLabel(res?.source_label || GLOSSARY_SOURCE_LABEL)
      })
      .catch(() => {
        if (active) {
          setEntries(FALLBACK_GLOSSARY_ENTRIES)
          setSourceLabel(GLOSSARY_SOURCE_LABEL)
        }
      })
    return () => {
      active = false
    }
  }, [open])

  if (!open) return null

  const query = search.trim().toLowerCase()
  const filtered = entries.filter((entry) => {
    if (!query) return true
    return (
      entry.term.toLowerCase().includes(query) ||
      entry.plain.toLowerCase().includes(query) ||
      entry.example.toLowerCase().includes(query) ||
      entry.what_office_asks.toLowerCase().includes(query) ||
      entry.related_fields.some((f) => f.toLowerCase().includes(query))
    )
  })

  return (
    <Card data-testid="glossary-drawer" className="border-blue-200 bg-slate-50">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Commercialization & policy glossary</CardTitle>
            <Badge variant="warning" data-testid="glossary-source-badge">
              {sourceLabel}
            </Badge>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            data-testid="close-glossary-button"
          >
            Close glossary
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <input
          type="text"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white"
          placeholder="Filter concepts (e.g., novelty, prior art, inventorship, conflict of interest)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          data-testid="glossary-search"
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filtered.map((entry) => (
            <div
              key={entry.term}
              className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5"
              data-testid={`glossary-entry-${entry.term.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-sm font-semibold text-slate-900">{entry.term}</h4>
                <span className="text-xs text-slate-500">
                  {entry.reviewed_by && entry.reviewed_on
                    ? `Reviewed by ${entry.reviewed_by} (${entry.reviewed_on})`
                    : entry.reviewed_by
                      ? `Reviewed by ${entry.reviewed_by}`
                      : 'Draft (unreviewed)'}
                </span>
              </div>
              <p className="text-sm text-slate-700">{entry.plain}</p>
              <p className="text-xs text-slate-600">
                <span className="font-medium text-slate-700">Example:</span> {entry.example}
              </p>
              <p className="text-xs text-slate-600">
                <span className="font-medium text-slate-700">What the office asks:</span>{' '}
                {entry.what_office_asks}
              </p>
              {entry.related_fields.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {entry.related_fields.map((fieldId) => (
                    <Badge key={fieldId} variant="neutral">
                      {fieldId}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <p className="text-sm text-slate-500">No glossary entries match “{search}”.</p>
        )}
      </CardContent>
    </Card>
  )
}

export default GlossaryDrawer
