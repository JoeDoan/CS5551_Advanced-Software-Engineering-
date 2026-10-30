import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { FairnessAnalyticsPanel } from '../FairnessAnalyticsPanel'
import { RoomUtilizationChart } from '../RoomUtilizationChart'

describe('Sprint 3 Admin Analytics Panels', () => {
  it('renders FairnessAnalyticsPanel and filters instructors by department', async () => {
    render(<FairnessAnalyticsPanel semesterId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Dr. Alice Smith')).toBeInTheDocument()
      expect(screen.getByText('Dr. Carol Williams')).toBeInTheDocument()
    })

    expect(screen.getByText(/Gini Index: 0.0312/i)).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('fairness-dept-filter'), {
      target: { value: 'ECE' },
    })

    expect(screen.getByText('Dr. Carol Williams')).toBeInTheDocument()
    expect(screen.queryByText('Dr. Alice Smith')).not.toBeInTheDocument()
  })

  it('renders RoomUtilizationChart and filters rooms by utilization tier', async () => {
    render(<RoomUtilizationChart semesterId={1} />)

    await waitFor(() => {
      expect(screen.getByText('RH 204')).toBeInTheDocument()
      expect(screen.getByText('FH 256')).toBeInTheDocument()
      expect(screen.getByText('SCB 205')).toBeInTheDocument()
    })

    fireEvent.change(screen.getByTestId('utilization-tier-filter'), {
      target: { value: 'heavily_booked' },
    })

    expect(screen.getByText('FH 256')).toBeInTheDocument()
    expect(screen.queryByText('RH 204')).not.toBeInTheDocument()
  })
})
