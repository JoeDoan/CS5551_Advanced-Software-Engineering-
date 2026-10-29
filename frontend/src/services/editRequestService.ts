import { apiClient } from './apiClient';
import {
  EditRequest,
  EditRequestCreatePayload,
  EditRequestReviewPayload,
} from '../types/api';

const FALLBACK_EDIT_REQUESTS: EditRequest[] = [
  {
    id: 1,
    schedule_id: 1,
    requester_id: 1,
    requested_changes: 'Requesting room FH-206 due to projector requirement for CS 101.',
    status: 'pending',
    created_at: '2026-10-15T14:20:00Z',
  },
  {
    id: 2,
    schedule_id: 4,
    requester_id: 3,
    requested_changes: 'Move CS 404 from early morning TR slot to afternoon TR 13:00-14:15.',
    status: 'approved',
    created_at: '2026-10-14T09:15:00Z',
  },
];

let localRequestsStore: EditRequest[] = [...FALLBACK_EDIT_REQUESTS];

export interface EditRequestFilterParams {
  status?: 'pending' | 'approved' | 'rejected';
  requester_id?: number;
  schedule_id?: number;
}

export const editRequestService = {
  async getEditRequests(filters?: EditRequestFilterParams): Promise<EditRequest[]> {
    try {
      const response = await apiClient.get<EditRequest[]>('/edit-requests', {
        params: filters,
      });
      if (Array.isArray(response.data)) {
        localRequestsStore = response.data;
        return response.data;
      }
      return localRequestsStore;
    } catch {
      let data = [...localRequestsStore];
      if (filters?.status) {
        data = data.filter((r) => r.status === filters.status);
      }
      if (filters?.requester_id !== undefined) {
        data = data.filter((r) => r.requester_id === filters.requester_id);
      }
      if (filters?.schedule_id !== undefined) {
        data = data.filter((r) => r.schedule_id === filters.schedule_id);
      }
      return data;
    }
  },

  async createEditRequest(payload: EditRequestCreatePayload): Promise<EditRequest> {
    try {
      const response = await apiClient.post<EditRequest>('/edit-requests', payload);
      localRequestsStore = [response.data, ...localRequestsStore];
      return response.data;
    } catch {
      const created: EditRequest = {
        id: Date.now(),
        schedule_id: payload.schedule_id,
        requester_id: payload.requester_id,
        requested_changes: payload.requested_changes,
        proposed_room_id: payload.proposed_room_id,
        proposed_time_slot_id: payload.proposed_time_slot_id,
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      localRequestsStore = [created, ...localRequestsStore];
      return created;
    }
  },

  async reviewEditRequest(
    requestId: number,
    payload: EditRequestReviewPayload
  ): Promise<EditRequest> {
    try {
      const response = await apiClient.patch<EditRequest>(
        `/edit-requests/${requestId}/review`,
        payload
      );
      localRequestsStore = localRequestsStore.map((r) =>
        r.id === requestId ? response.data : r
      );
      return response.data;
    } catch {
      const updated: EditRequest = {
        id: requestId,
        schedule_id: 1,
        requester_id: 1,
        requested_changes: 'Updated locally',
        ...localRequestsStore.find((r) => r.id === requestId),
        status: payload.status,
        reviewer_notes: payload.reviewer_notes,
      };
      localRequestsStore = localRequestsStore.map((r) =>
        r.id === requestId ? updated : r
      );
      return updated;
    }
  },

  async deleteEditRequest(requestId: number): Promise<void> {
    try {
      await apiClient.delete(`/edit-requests/${requestId}`);
    } finally {
      localRequestsStore = localRequestsStore.filter((r) => r.id !== requestId);
    }
  },
};

