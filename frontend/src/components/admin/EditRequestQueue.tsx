import React, { useEffect, useMemo, useState } from 'react'
import { Check, X, Inbox, Search, ArrowRightLeft, User } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../ui'
import { Toast } from '../common/Toast'
import { EditRequest } from '../../types/api'
import { editRequestService } from '../../services/editRequestService'
import { useAuth } from '../../context/AuthContext'

export const EditRequestQueue: React.FC = () => {
  const { user } = useAuth()
  const isCoordinator = (user?.role ?? 'coordinator') === 'coordinator'
  const canFilterMine = !isCoordinator && user?.linked_user_id != null

  const [requests, setRequests] = useState<EditRequest[]>([])
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'pending' | 'approved' | 'rejected'>('ALL')
  const [ownerFilter, setOwnerFilter] = useState<'ALL' | 'MINE'>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const loadRequests = async () => {
    setLoading(true)
    try {
      const data = await editRequestService.getEditRequests()
      setRequests(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRequests()
  }, [])

  const handleReview = async (id: number, status: 'approved' | 'rejected') => {
    try {
      const updated = await editRequestService.reviewEditRequest(id, { status })
      setRequests((prev) => prev.map((r) => (r.id === id ? { ...r, ...updated } : r)))
      setToast({
        type: 'success',
        message: `Edit request #${id} ${status}.`,
      })
    } catch (err) {
      setToast({
        type: 'error',
        message: (err as Error).message || 'Failed to update edit request.',
      })
    }
  }

  const filteredRequests = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return requests.filter((r) => {
      if (statusFilter !== 'ALL' && r.status !== statusFilter) {
        return false
      }
      if (canFilterMine && ownerFilter === 'MINE' && r.requester_id !== user?.linked_user_id) {
        return false
      }
      if (!q) return true

      const searchable = [
        r.course_code,
        r.course_name,
        r.requester_name,
        r.requested_changes,
        r.current_room_number,
        r.current_time_slot,
        r.proposed_room_number,
        r.proposed_time_slot,
        `schedule #${r.schedule_id}`,
        `request #${r.id}`,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return searchable.includes(q)
    })
  }, [requests, statusFilter, canFilterMine, ownerFilter, user?.linked_user_id, searchQuery])

  const pendingCount = requests.filter((r) => r.status === 'pending').length

  return (
    <Card hoverable data-testid="edit-request-queue">
      <CardHeader className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600">
            <Inbox className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Instructor Schedule Edit Requests</CardTitle>
            <p className="text-xs text-slate-500">
              {isCoordinator
                ? `Review post-scheduling room or slot modification requests (${pendingCount} pending)`
                : `Track status of submitted schedule modification requests (${pendingCount} pending)`}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {canFilterMine && (
            <div className="inline-flex rounded-xl border border-slate-200 bg-slate-100 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setOwnerFilter('ALL')}
                data-testid="edit-requests-all-btn"
                className={`px-2.5 py-1 rounded-lg font-semibold transition-colors ${
                  ownerFilter === 'ALL'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Requests
              </button>
              <button
                type="button"
                onClick={() => setOwnerFilter('MINE')}
                data-testid="edit-requests-mine-btn"
                className={`px-2.5 py-1 rounded-lg font-semibold transition-colors ${
                  ownerFilter === 'MINE'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                My Requests
              </button>
            </div>
          )}

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search requests by course, instructor, or note..."
              aria-label="Search schedule edit requests"
              data-testid="edit-request-search-input"
              className="rounded-xl border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 w-64 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <select
            aria-label="Filter edit requests by status"
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as 'ALL' | 'pending' | 'approved' | 'rejected')
            }
            className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <option value="ALL">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </CardHeader>

      <CardContent>
        {loading ? (
          <p className="text-xs text-slate-500 py-4">Loading edit requests...</p>
        ) : filteredRequests.length === 0 ? (
          <p className="text-xs text-slate-500 py-4">No schedule edit requests match the filter.</p>
        ) : (
          <div className="space-y-3">
            {filteredRequests.map((req) => {
              const courseHeading = req.course_code
                ? `${req.course_code}${req.course_name ? ` — ${req.course_name}` : ''}`
                : `Schedule #${req.schedule_id}`
              const currentSummary = [req.current_room_number, req.current_time_slot]
                .filter(Boolean)
                .join(' • ')
              const proposedSummary = [req.proposed_room_number, req.proposed_time_slot]
                .filter(Boolean)
                .join(' • ')

              return (
                <div
                  key={req.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/60"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">{courseHeading}</span>
                      <span className="text-[11px] font-medium text-slate-400">
                        Request #{req.id}
                      </span>
                      <Badge
                        variant={
                          req.status === 'approved'
                            ? 'success'
                            : req.status === 'rejected'
                              ? 'danger'
                              : 'warning'
                        }
                        dot
                      >
                        {req.status.toUpperCase()}
                      </Badge>
                      {req.requester_name && (
                        <Badge variant="neutral">
                          <User className="w-3 h-3 mr-1 inline" />
                          {req.requester_name}
                        </Badge>
                      )}
                    </div>

                    {(currentSummary || proposedSummary) && (
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        {currentSummary && (
                          <Badge variant="neutral">Current: {currentSummary}</Badge>
                        )}
                        {proposedSummary && (
                          <Badge variant="info">
                            <ArrowRightLeft className="w-3 h-3 mr-1 inline" />
                            Proposed: {proposedSummary}
                          </Badge>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-slate-600">{req.requested_changes}</p>
                  </div>

                  {isCoordinator ? (
                    req.status === 'pending' && (
                      <div className="flex items-center space-x-2 shrink-0">
                        <Button
                          variant="primary"
                          size="sm"
                          leftIcon={<Check className="w-3.5 h-3.5" />}
                          onClick={() => handleReview(req.id, 'approved')}
                          data-testid={`approve-request-${req.id}`}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          leftIcon={<X className="w-3.5 h-3.5" />}
                          onClick={() => handleReview(req.id, 'rejected')}
                          data-testid={`reject-request-${req.id}`}
                        >
                          Reject
                        </Button>
                      </div>
                    )
                  ) : (
                    <div className="shrink-0">
                      <Badge variant="neutral" data-testid={`readonly-request-status-${req.id}`}>
                        {req.status}
                      </Badge>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </CardContent>

      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}
    </Card>
  )
}

export default EditRequestQueue
