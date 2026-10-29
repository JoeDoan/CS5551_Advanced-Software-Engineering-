import React, { useState } from 'react'
import { Calendar, Clock, MapPin, User, FileEdit } from 'lucide-react'
import { Modal, Button, Badge, Alert } from '../ui'
import { ScheduleEvent } from '../../types/api'
import { editRequestService } from '../../services/editRequestService'

export interface EventDetailModalProps {
  isOpen: boolean
  event: ScheduleEvent | null
  onClose: () => void
  onRequestSubmitted?: () => void
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({
  isOpen,
  event,
  onClose,
  onRequestSubmitted,
}) => {
  const [requestedChanges, setRequestedChanges] = useState('')
  const [requesterId, setRequesterId] = useState<number>(1)
  const [submitting, setSubmitting] = useState(false)
  const [submittedSuccess, setSubmittedSuccess] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  if (!event) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!requestedChanges.trim()) {
      setErrorMsg('Please describe the requested schedule change.')
      return
    }
    setSubmitting(true)
    setErrorMsg(null)
    try {
      await editRequestService.createEditRequest({
        schedule_id: event.id,
        requester_id: requesterId,
        requested_changes: requestedChanges.trim(),
      })
      setSubmittedSuccess(true)
      setRequestedChanges('')
      onRequestSubmitted?.()
    } catch {
      setErrorMsg('Unable to submit edit request. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleClose = () => {
    setSubmittedSuccess(false)
    setErrorMsg(null)
    setRequestedChanges('')
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`${event.course_code} — ${event.course_name}`}
      description="Scheduled course details and post-scheduling adjustment request"
    >
      <div className="space-y-5" data-testid="event-detail-modal">
        <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200/80 text-xs">
          <div className="flex items-start space-x-2.5">
            <User className="w-4 h-4 text-umkc-blue-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-slate-400 font-medium">Instructor</p>
              <p className="text-slate-800 font-semibold mt-0.5">{event.instructor_name}</p>
            </div>
          </div>

          <div className="flex items-start space-x-2.5">
            <MapPin className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-slate-400 font-medium">Classroom / Lab</p>
              <p className="text-slate-800 font-semibold mt-0.5">{event.room_number}</p>
            </div>
          </div>

          <div className="flex items-start space-x-2.5">
            <Calendar className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-slate-400 font-medium">Meeting Days</p>
              <p className="text-slate-800 font-semibold mt-0.5">{event.day_pattern}</p>
            </div>
          </div>

          <div className="flex items-start space-x-2.5">
            <Clock className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-slate-400 font-medium">Time Slot</p>
              <p className="text-slate-800 font-semibold mt-0.5">
                {event.start_time} – {event.end_time}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs px-1">
          <span className="text-slate-500 font-medium">Assignment Status</span>
          <Badge variant={event.status === 'confirmed' ? 'success' : 'gold'} dot>
            {event.status.toUpperCase()}
          </Badge>
        </div>

        <div className="border-t border-slate-200 pt-4">
          <div className="flex items-center space-x-2 mb-3">
            <FileEdit className="w-4 h-4 text-umkc-blue-700" />
            <h4 className="text-sm font-bold text-slate-800">Submit Schedule Edit Request</h4>
          </div>

          {submittedSuccess && (
            <Alert variant="success" title="Edit Request Queued">
              Your schedule modification request has been submitted for Coordinator review.
            </Alert>
          )}

          {errorMsg && (
            <Alert variant="danger" title="Submission Error">
              {errorMsg}
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-3 mt-3">
            <div>
              <label
                htmlFor="edit-requester-id"
                className="block text-xs font-medium text-slate-700 mb-1"
              >
                Faculty Requester ID
              </label>
              <input
                id="edit-requester-id"
                type="number"
                min={1}
                max={20}
                value={requesterId}
                onChange={(e) => setRequesterId(Number(e.target.value) || 1)}
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs text-slate-800"
              />
            </div>

            <div>
              <label
                htmlFor="edit-request-changes"
                className="block text-xs font-medium text-slate-700 mb-1"
              >
                Requested Modification (Room / Time Slot / Justification)
              </label>
              <textarea
                id="edit-request-changes"
                rows={3}
                value={requestedChanges}
                onChange={(e) => setRequestedChanges(e.target.value)}
                placeholder="e.g., Requesting move to FH-206 or afternoon TR 13:00-14:15 slot due to lab overlap"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-umkc-blue-500"
                data-testid="edit-request-textarea"
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <Button type="button" variant="secondary" size="sm" onClick={handleClose}>
                Close
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={submitting}
                data-testid="submit-edit-request-button"
              >
                Submit Edit Request
              </Button>
            </div>
          </form>
        </div>
      </div>
    </Modal>
  )
}

export default EventDetailModal

