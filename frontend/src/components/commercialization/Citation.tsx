import React from 'react'
import { Badge } from '../ui'
import { PolicyCitation } from '../../services/commercializationService'

/** One quoted policy passage with its source, version and who it applies to. */
export const Citation: React.FC<{ c: PolicyCitation }> = ({ c }) => (
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

export default Citation
