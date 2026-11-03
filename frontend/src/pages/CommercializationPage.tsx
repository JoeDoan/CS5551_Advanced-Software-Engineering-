import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { AuthRole } from '../types/api'
import { DropExtract } from '../components/commercialization/DropExtract'
import { Refine } from '../components/commercialization/Refine'
import { Validate } from '../components/commercialization/Validate'
import { ExportPackage } from '../components/commercialization/ExportPackage'
import {
  Answers,
  CommercializationStatus,
  DraftResult,
  commercializationService,
} from '../services/commercializationService'

type Step = 'drop' | 'refine' | 'validate' | 'export'

const STEPS: { id: Step; label: string }[] = [
  { id: 'drop', label: '1. Drop & extract' },
  { id: 'refine', label: '2. Questions & compliance' },
  { id: 'validate', label: '3. Market & IP' },
  { id: 'export', label: '4. Export' },
]

export const CommercializationPage: React.FC = () => {
  const { user } = useAuth()
  const role: AuthRole = user?.role ?? 'coordinator'
  const [step, setStep] = useState<Step>('drop')
  const [status, setStatus] = useState<CommercializationStatus | null>(null)
  const [draft, setDraft] = useState<DraftResult | null>(null)
  const [answers, setAnswers] = useState<Answers>({})

  useEffect(() => {
    commercializationService.getStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  return (
    <div className="space-y-6" data-testid="commercialization-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Commercialization Advisor</h1>
        <p className="text-sm text-slate-500 mt-1">
          Turn a paper into a draft invention disclosure, check outside-activity and ownership policy, and
          explore markets. A draft to help you prepare, not legal advice.
        </p>
      </div>

      <div className="flex gap-2 border-b border-slate-200" role="tablist">
        {STEPS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={step === s.id}
            onClick={() => setStep(s.id)}
            data-testid={`step-${s.id}`}
            className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              step === s.id
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {step === 'drop' && <DropExtract status={status} draft={draft} onDraft={setDraft} />}
      {step === 'refine' && (
        <Refine draft={draft} role={role} userName={user?.full_name ?? ''} onAnswers={setAnswers} />
      )}
      {step === 'validate' && <Validate draft={draft} />}
      {step === 'export' && <ExportPackage draft={draft} answers={answers} />}
    </div>
  )
}

export default CommercializationPage
