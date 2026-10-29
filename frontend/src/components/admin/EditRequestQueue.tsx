import React, { useEffect, useState } from 'react'
import { Check, X, Inbox } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../ui'
import { EditRequest } from '../../types/api'
import { editRequestService } from '../../services/editRequestService'

export const EditRequestQueue: React.FC = () => {
  const [requests, setRequests] = useState<EditRequest[]>([])
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'pending' | 'approved' | 'rejected'>('ALL')
  const [loading, setLoading] = useState<boolean>(true)

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
    const updated = await editRequestService.reviewEditRequest(id, { status })
    setRequests((prev) => prev.map((r) => (r.id === id ? updated : r)))
  }

  const filteredRequests = requests.filter((r) =>
    statusFilter === 'ALL' ? true : r.status === statusFilter
  )

  const pendingCount = requests.filter((r) => r.status === 'pending').length

  return (
    <Card hoverable data-testid="edit-request-queue">
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-600">
            <Inbox className="w-5 h-5" />
          </div>
          <div>
            <CardTitle>Instructor Schedule Edit Requests</CardTitle>
            <p className="text-xs text-slate-500">
              Review post-scheduling room or slot modification requests ({pendingCount} pending)
            </p>
          </div>
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
      </CardHeader>

      <CardContent>
        {loading ? (
          <p className="text-xs text-slate-500 py-4">Loading edit requests...</p>
        ) : filteredRequests.length === 0 ? (
          <p className="text-xs text-slate-500 py-4">No schedule edit requests match the filter.</p>
        ) : (
          <div className="space-y-3">
            {filteredRequests.map((req) => (
              <div
                key={req.id}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/60"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-800">
                      Request #{req.id} (Schedule #{req.schedule_id})
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
                  </div>
                  <p className="text-xs text-slate-600">{req.requested_changes}</p>
                </div>

                {req.status === 'pending' && (
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
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default EditRequestQueue

