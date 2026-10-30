import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { CourseManager } from '../CourseManager'

describe('CourseManager Component', () => {
  it('renders course table and filters by search query', async () => {
    render(<CourseManager />)

    await waitFor(() => {
      expect(screen.getByText('CS 101')).toBeInTheDocument()
      expect(screen.getByText('ECE 448')).toBeInTheDocument()
    })

    const searchInput = screen.getByTestId('course-search-input')
    fireEvent.change(searchInput, { target: { value: 'Embedded' } })

    expect(screen.getByText('ECE 448')).toBeInTheDocument()
    expect(screen.queryByText('CS 101')).not.toBeInTheDocument()
  })

  it('creates a new course via modal and deletes an existing course', async () => {
    render(<CourseManager />)

    await waitFor(() => {
      expect(screen.getByText('CS 101')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('add-course-btn'))
    fireEvent.change(screen.getByTestId('modal-course-code'), { target: { value: 'CS 490' } })
    fireEvent.change(screen.getByTestId('modal-course-name'), { target: { value: 'Special Topics' } })
    fireEvent.click(screen.getByTestId('save-course-btn'))

    await waitFor(() => {
      expect(screen.getByText('CS 490')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('delete-course-1'))
    await waitFor(() => {
      expect(screen.queryByText('CS 101')).not.toBeInTheDocument()
    })
  })
})
