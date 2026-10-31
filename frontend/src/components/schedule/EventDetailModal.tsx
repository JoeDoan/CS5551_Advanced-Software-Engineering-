import React, { useEffect, useState } from 'react'
import { Link, useInRouterContext } from 'react-router-dom'
import {
  Calendar,
  Clock,
  MapPin,
  User,
  FileEdit,
  Settings2,
  ExternalLink,
} from 'lucide-react'
import { Modal, Button, Badge, Alert } from '../ui'
import {
  EditRequestCreatePayload,
  Room,
  ScheduleEvent,
  TimeSlot,
} from '../../types/api'
import { useAuth } from '../../context/AuthContext'
import { editRequestService } from '../../services/editRequestService'
import { roomService } from '../../services/roomService'
import { timeSlotService } from '../../services/timeSlotService'
import { formatRoomWithBuilding } from '../../utils/academicDomain'

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
  const { user, isStandaloneFallback } = useAuth()
  const inRouter = useInRouterContext()

  const [requestedChanges, setRequestedChanges] = useState('')
  const [proposedRoomId, setProposedRoomId] = useState('')
  const [proposedSlotId, setProposedSlotId] = useState('')
  const [rooms, setRooms] = useState<Room[]>([])
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [submittedSuccess, setSubmittedSuccess] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const isCoordinatorSession = !isStandaloneFallback && user?.role === 'coordinator'

  useEffect(() => {
    setRequestedChanges('')
    setProposedRoomId('')
    setProposedSlotId('')
    setSubmittedSuccess(false)
    setErrorMsg(null)
  }, [event?.id])

  useEffect(() => {
    if (!isOpen || isCoordinatorSession) {
      return
    }
    let active = true
    const loadCatalogs = async () => {
      try {
        const loadSlots =
          typeof timeSlotService.getAllTimeSlots === 'function'
            ? timeSlotService.getAllTimeSlots()
            : timeSlotService.getTimeSlots()
        const [loadedRooms, loadedSlots] = await Promise.all([
          roomService.getRooms(),
          loadSlots,
        ])
        if (!active) return
        setRooms(loadedRooms)
        setTimeSlots(loadedSlots)
      } catch {
        if (!active) return
        setRooms([])
        setTimeSlots([])
      }
    }
    loadCatalogs()
    return () => {
      active = false
    }
  }, [isOpen, isCoordinatorSession])

  if (!event) return null

  const effectiveRequesterId =
    user?.linked_user_id ?? event.user_id ?? event.instructor_id ?? 1

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!requestedChanges.trim()) {
      setErrorMsg('Please describe the requested schedule change.')
      return
    }
    setSubmitting(true)
    setErrorMsg(null)
    try {
      const payload: EditRequestCreatePayload = {
        schedule_id: event.id,
        requester_id: effectiveRequesterId,
        requested_changes: requestedChanges.trim(),
      }
      if (proposedRoomId !== '') {
        payload.proposed_room_id = Number(proposedRoomId)
      }
      if (proposedSlotId !== '') {
        payload.proposed_time_slot_id = Number(proposedSlotId)
      }
      await editRequestService.createEditRequest(payload)
      setSubmittedSuccess(true)
      setRequestedChanges('')
      setProposedRoomId('')
      setProposedSlotId('')
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
    setProposedRoomId('')
    setProposedSlotId('')
    onClose()
  }

  const manageSectionsClassName =
    'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-150 px-3 py-1.5 text-xs gap-1.5 bg-umkc-blue-700 hover:bg-umkc-blue-800 text-white shadow-sm'

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`${event.course_code} — ${event.course_name}`}
      description="Scheduled course details and post-scheduling adjustment controls"
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
          {isCoordinatorSession ? (
            <div
              data-testid="coordinator-section-controls"
              className="rounded-xl border border-blue-200 bg-blue-50/60 p-4 space-y-3"
            >
              <div className="flex items-center space-x-2">
                <Settings2 className="w-4 h-4 text-umkc-blue-700" />
                <h4 className="text-sm font-bold text-slate-900">
                  Coordinator Section Controls
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                As a Course Coordinator, you can directly modify classroom assignments, time slots, and faculty assignments in Scheduled Sections without queuing an edit request.
              </p>
              <div className="flex justify-end items-center gap-2 pt-1">
                <Button type="button" variant="secondary" size="sm" onClick={handleClose}>
                  Close
                </Button>
                {inRouter ? (
                  <Link
                    to="/courses"
                    onClick={handleClose}
                    data-testid="manage-sections-link"
                    className={manageSectionsClassName}
                  >
                    <span>Manage in Scheduled Sections</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                ) : (
                  <a
                    href="/courses"
                    data-testid="manage-sections-link"
                    className={manageSectionsClassName}
                  >
                    <span>Manage in Scheduled Sections</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex items-center space-x-2">
                  <FileEdit className="w-4 h-4 text-umkc-blue-700" />
                  <h4 className="text-sm font-bold text-slate-800">
                    Submit Schedule Edit Request
                  </h4>
                </div>
                {!isStandaloneFallback && user?.full_name && (
                  <span
                    data-testid="requester-identity"
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-semibold text-slate-700"
                  >
                    Requester: {user.full_name}
                  </span>
                )}
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
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="proposed-room-select"
                      className="block text-xs font-medium text-slate-700 mb-1"
                    >
                      Proposed Classroom (Optional)
                    </label>
                    <select
                      id="proposed-room-select"
                      data-testid="proposed-room-select"
                      value={proposedRoomId}
                      onChange={(e) => setProposedRoomId(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-umkc-blue-500"
                    >
                      <option value="">Keep current ({event.room_number})</option>
                      {rooms.map((room) => (
                        <option key={room.id} value={String(room.id)}>
                          {formatRoomWithBuilding(room)} (Cap {room.capacity})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="proposed-slot-select"
                      className="block text-xs font-medium text-slate-700 mb-1"
                    >
                      Proposed Time Slot (Optional)
                    </label>
                    <select
                      id="proposed-slot-select"
                      data-testid="proposed-slot-select"
                      value={proposedSlotId}
                      onChange={(e) => setProposedSlotId(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-umkc-blue-500"
                    >
                      <option value="">
                        Keep current ({event.day_pattern} {event.start_time}–{event.end_time})
                      </option>
                      {timeSlots.map((slot) => (
                        <option key={slot.id} value={String(slot.id)}>
                          {slot.day_pattern} {slot.start_time} – {slot.end_time}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="edit-request-changes"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Requested Modification & Justification
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
            </>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default EventDetailModal
