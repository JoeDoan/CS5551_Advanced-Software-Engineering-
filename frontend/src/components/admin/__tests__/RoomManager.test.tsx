import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { RoomManager } from '../RoomManager'

describe('RoomManager Component', () => {
  it('renders room inventory and filters by room type', async () => {
    render(<RoomManager />)

    await waitFor(() => {
      expect(screen.getByText('RH 204')).toBeInTheDocument()
      expect(screen.getByText('FH 464')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('room-type-filter'), { target: { value: 'lab' } })
    expect(screen.getByText('FH 464')).toBeInTheDocument()
    expect(screen.queryByText('RH 204')).not.toBeInTheDocument()
  })

  it('adds a new room via modal and deletes a room', async () => {
    render(<RoomManager />)

    await waitFor(() => {
      expect(screen.getByText('RH 204')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('add-room-btn'))
    fireEvent.change(screen.getByTestId('modal-room-number'), { target: { value: 'FH 501' } })
    fireEvent.click(screen.getByTestId('save-room-btn'))

    await waitFor(() => {
      expect(screen.getByText('FH 501')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('delete-room-1'))
    await waitFor(() => {
      expect(screen.queryByText('RH 204')).not.toBeInTheDocument()
    })
  })
})
