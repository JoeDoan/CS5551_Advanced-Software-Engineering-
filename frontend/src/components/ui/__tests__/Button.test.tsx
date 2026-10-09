import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '../Button'

describe('Button UI Component', () => {
  it('renders button text correctly', () => {
    render(<Button>Generate Schedule</Button>)
    expect(screen.getByRole('button', { name: /generate schedule/i })).toBeInTheDocument()
  })

  it('renders gold variant with appropriate classes', () => {
    render(<Button variant="gold">UMKC Gold Button</Button>)
    const button = screen.getByRole('button', { name: /umkc gold button/i })
    expect(button.className).toContain('bg-umkc-gold-500')
  })

  it('handles click events properly', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click Me</Button>)
    fireEvent.click(screen.getByRole('button', { name: /click me/i }))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled and shows loader when isLoading is true', () => {
    const handleClick = vi.fn()
    render(
      <Button isLoading onClick={handleClick}>
        Saving...
      </Button>
    )
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(handleClick).not.toHaveBeenCalled()
  })
})
