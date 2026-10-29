import { describe, it, expect, vi, beforeEach } from 'vitest'
import { editRequestService } from '../editRequestService'
import { apiClient } from '../apiClient'

vi.mock('../apiClient', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('editRequestService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches edit requests from API when online', async () => {
    const mockList = [
      {
        id: 10,
        schedule_id: 2,
        requester_id: 4,
        requested_changes: 'Swap to afternoon slot',
        status: 'pending',
      },
    ]
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockList })

    const res = await editRequestService.getEditRequests({ status: 'pending' })
    expect(apiClient.get).toHaveBeenCalledWith('/edit-requests', {
      params: { status: 'pending' },
    })
    expect(res).toEqual(mockList)
  })

  it('creates and reviews edit requests with offline fallback', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network error'))
    const created = await editRequestService.createEditRequest({
      schedule_id: 5,
      requester_id: 2,
      requested_changes: 'Move to room RH-215',
    })
    expect(created.schedule_id).toBe(5)
    expect(created.status).toBe('pending')

    vi.mocked(apiClient.patch).mockRejectedValue(new Error('Network error'))
    const reviewed = await editRequestService.reviewEditRequest(created.id, {
      status: 'approved',
      reviewer_notes: 'Approved by Coordinator',
    })
    expect(reviewed.status).toBe('approved')
    expect(reviewed.reviewer_notes).toBe('Approved by Coordinator')
  })
})

