import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Select } from '../Select'

describe('Select UI Component', () => {
  const options = [
    { value: 'cs', label: 'Computer Science' },
    { value: 'math', label: 'Mathematics' },
    { value: 'ece', label: 'Electrical Engineering' },
  ]

  it('renders select with options and label', () => {
    render(
      <Select
        label="Department"
        options={options}
        defaultValue="cs"
      />
    )

    expect(screen.getByLabelText(/department/i)).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByText('Computer Science')).toBeInTheDocument()
    expect(screen.getByText('Mathematics')).toBeInTheDocument()
  })

  it('handles value changes', () => {
    const handleChange = vi.fn()
    render(
      <Select
        label="Department"
        options={options}
        onChange={handleChange}
      />
    )

    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'math' } })
    expect(handleChange).toHaveBeenCalled()
    expect((select as HTMLSelectElement).value).toBe('math')
  })

  it('renders error message when error prop is provided', () => {
    render(
      <Select
        label="Department"
        options={options}
        error="Please select a valid department"
      />
    )

    expect(screen.getByText('Please select a valid department')).toBeInTheDocument()
  })
})
