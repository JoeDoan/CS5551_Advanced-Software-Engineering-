import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../Card'

describe('Card UI Component', () => {
  it('renders card content structure properly', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Schedule Summary</CardTitle>
          <CardDescription>Term details for Fall 2024</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Main card content</p>
        </CardContent>
        <CardFooter>
          <span>Footer Actions</span>
        </CardFooter>
      </Card>
    )

    expect(screen.getByText('Schedule Summary')).toBeInTheDocument()
    expect(screen.getByText('Term details for Fall 2024')).toBeInTheDocument()
    expect(screen.getByText('Main card content')).toBeInTheDocument()
    expect(screen.getByText('Footer Actions')).toBeInTheDocument()
  })

  it('applies hoverable styles when hoverable prop is set', () => {
    const { container } = render(<Card hoverable>Hover card</Card>)
    const cardEl = container.firstChild as HTMLElement
    expect(cardEl.className).toContain('hover:shadow-card-hover')
  })
})
