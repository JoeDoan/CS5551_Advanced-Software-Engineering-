import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Input } from '../Input'

describe('Input UI Component', () => {
  it('renders input with label and helper text', () => {
    render(
      <Input
        label="Course Code"
        placeholder="e.g. CS 5551"
        helperText="Enter official course code"
      />
    )

    expect(screen.getByLabelText(/course code/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('e.g. CS 5551')).toBeInTheDocument()
    expect(screen.getByText('Enter official course code')).toBeInTheDocument()
  })

  it('renders error state and error message', () => {
    render(
      <Input
        label="Course Code"
        error="Course code is required"
      />
    )

    expect(screen.getByText('Course code is required')).toBeInTheDocument()
    const input = screen.getByLabelText(/course code/i)
    expect(input.className).toContain('border-red-300')
  })

  it('handles user input change events', () => {
    const handleChange = vi.fn()
    render(<Input label="Room Number" onChange={handleChange} />)
    const input = screen.getByLabelText(/room number/i)

    fireEvent.change(input, { target: { value: 'RH 204' } })
    expect(handleChange).toHaveBeenCalled()
    expect((input as HTMLInputElement).value).toBe('RH 204')
  })
})
