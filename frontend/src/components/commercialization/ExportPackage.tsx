import React, { useState } from 'react'
import { Alert, Button, Card, CardContent, CardHeader, CardTitle } from '../ui'
import { Answers, DraftResult, commercializationService, fieldValue } from '../../services/commercializationService'
import { errorMessage } from '../../services/insightsService'

const FILE_LIST = [
  '01_UM16C_Draft_IDF.md and .html (open the .html and print to PDF)',
  '02_Prior_Art_and_Market_Report.md',
  '03_COI_Compliance_Checklist_Cited.md',
  '04_Non_Confidential_Summary_1Page.md',
  '05_raw_submission_bundle.json',
]

export const ttoEmail = (draft: DraftResult): string => /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/.exec(draft.returns_to)?.[0] ?? ''

export const buildMailto = (draft: DraftResult): string => {
  const title = fieldValue(draft, 'A1_title') || 'Invention disclosure'
  const subject = `Invention disclosure: ${title}`
  const body = 'Please find my draft invention disclosure attached (commercialization_package.zip).'
  return `mailto:${ttoEmail(draft)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

export interface ExportPackageProps {
  draft: DraftResult | null
  answers: Answers
}

export const ExportPackage: React.FC<ExportPackageProps> = ({ draft, answers }) => {
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!draft) {
    return (
      <Alert variant="info" data-testid="stage-export">
        Draft your disclosure in step 1 first. The package is built from it.
      </Alert>
    )
  }

  const download = async () => {
    setBusy(true)
    setError(null)
    setDone(false)
    try {
      const blob = await commercializationService.exportPackage(draft, answers)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'commercialization_package.zip'
      a.click()
      URL.revokeObjectURL(url)
      setDone(true)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4" data-testid="stage-export">
      <Card>
        <CardHeader>
          <CardTitle>Export your package</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            One zip with the files below. It is built on request and not saved on the server. Every file says it is
            a draft you must verify and is not legal advice.
          </p>
          <ul className="list-disc pl-4 text-sm text-slate-700">
            {FILE_LIST.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
          {error && <Alert variant="danger">{error}</Alert>}
          {done && <Alert variant="info">Downloaded. Check the contents before you send anything.</Alert>}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={download} disabled={busy} data-testid="export-download">
              {busy ? 'Building…' : 'Download package (.zip)'}
            </Button>
            <a
              className="text-sm underline text-blue-700"
              href={buildMailto(draft)}
              data-testid="export-mailto"
            >
              Email the Office of Technology Commercialization
            </a>
          </div>
          <p className="text-xs text-slate-500">
            There is no online portal to send to. Your email app opens with a message to the office; attach the
            zip yourself. Official form:{' '}
            <a className="underline" href={draft.form_url} target="_blank" rel="noreferrer">
              UM-16C
            </a>
            . Return to: {draft.returns_to}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
