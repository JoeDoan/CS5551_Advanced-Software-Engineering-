import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ScheduleFilters } from '../ScheduleFilters'

describe('ScheduleFilters Component', () => {
  it('renders department selector and search input', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    expect(screen.getByLabelText(/filter by department/i)).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/search by course code, instructor, or room/i)
    ).toBeInTheDocument()
    expect(handleFilterChange).toHaveBeenCalledWith({
      department: 'ALL',
      search: '',
    })
  })

  it('calls onFilterChange when department is changed', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    const select = screen.getByLabelText(/filter by department/i)
    fireEvent.change(select, { target: { value: 'CS' } })

    expect(handleFilterChange).toHaveBeenLastCalledWith({
      department: 'CS',
      search: '',
    })
  })

  it('calls onFilterChange when search input changes', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    const searchInput = screen.getByPlaceholderText(
      /search by course code, instructor, or room/i
    )
    fireEvent.change(searchInput, { target: { value: 'Lee' } })

    expect(handleFilterChange).toHaveBeenLastCalledWith({
      department: 'ALL',
      search: 'Lee',
    })
  })

  it('shows Reset button when filters are active and clears filters on click', () => {
    const handleFilterChange = vi.fn()
    render(<ScheduleFilters onFilterChange={handleFilterChange} />)

    // Reset button should not be present initially
    expect(screen.queryByRole('button', { name: /reset filters/i })).not.toBeInTheDocument()

    // Change department
    const select = screen.getByLabelText(/filter by department/i)
    fireEvent.change(select, { target: { value: 'MATH' } })

    // Reset button should now be visible
    const resetBtn = screen.getByRole('button', { name: /reset filters/i })
    expect(resetBtn).toBeInTheDocument()

    // Click Reset
    fireEvent.click(resetBtn)

    expect(handleFilterChange).toHaveBeenLastCalledWith({
      department: 'ALL',
      search: '',
    })
    expect(screen.queryByRole('button', { name: /reset filters/i })).not.toBeInTheDocument()
  })
})
