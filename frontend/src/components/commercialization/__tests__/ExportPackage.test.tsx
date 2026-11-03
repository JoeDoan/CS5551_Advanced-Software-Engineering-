import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ExportPackage, buildMailto, ttoEmail } from '../ExportPackage'
import { DraftResult, commercializationService } from '../../../services/commercializationService'

const draft = {
  fields: [{ id: 'A1_title', value: 'Acoustic crack sensing' }],
  flags: [],
  form_url: 'https://example.test/form.docx',
  returns_to: 'Office of Technology Commercialization, UMKC (ericwa@umkc.edu)',
} as unknown as DraftResult

describe('ExportPackage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('without a draft it asks for one', () => {
    render(<ExportPackage draft={null} answers={{}} />)
    expect(screen.getByText(/Draft your disclosure in step 1/)).toBeTruthy()
    expect(screen.queryByTestId('export-download')).toBeNull()
  })

  it('builds a mailto for the office from the form, with the title in the subject', () => {
    expect(ttoEmail(draft)).toBe('ericwa@umkc.edu')
    const href = buildMailto(draft)
    expect(href.startsWith('mailto:ericwa@umkc.edu?')).toBe(true)
    expect(decodeURIComponent(href)).toContain('Invention disclosure: Acoustic crack sensing')
  })

  it('downloads the zip built from the draft and the answers', async () => {
    const exp = vi
      .spyOn(commercializationService, 'exportPackage')
      .mockResolvedValue(new Blob(['zip'], { type: 'application/zip' }))
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    render(<ExportPackage draft={draft} answers={{ students: 'yes' }} />)
    fireEvent.click(screen.getByTestId('export-download'))
    await waitFor(() => expect(screen.getByText(/Downloaded/)).toBeTruthy())
    expect(exp).toHaveBeenCalledWith(draft, { students: 'yes' })
  })

  it('shows a failed export as a message', async () => {
    vi.spyOn(commercializationService, 'exportPackage').mockRejectedValue(new Error('Server unavailable.'))
    render(<ExportPackage draft={draft} answers={{}} />)
    fireEvent.click(screen.getByTestId('export-download'))
    await waitFor(() => expect(screen.getByText('Server unavailable.')).toBeTruthy())
  })
})
