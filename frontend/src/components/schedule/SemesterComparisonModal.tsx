import React from 'react'
import { ArrowRight } from 'lucide-react'
import { Modal, Badge, Button } from '../ui'
import { ScheduleEvent } from '../../types/api'
import { compareSemesters } from '../../utils/conflictDetector'

export interface SemesterComparisonModalProps {
  isOpen: boolean
  onClose: () => void
  baseSemesterLabel?: string
  targetSemesterLabel?: string
  baseEvents: ScheduleEvent[]
  targetEvents: ScheduleEvent[]
}

export const SemesterComparisonModal: React.FC<SemesterComparisonModalProps> = ({
  isOpen,
  onClose,
  baseSemesterLabel = 'Semester 1 (Fall 2024)',
  targetSemesterLabel = 'Semester 2 (Spring 2025)',
  baseEvents,
  targetEvents,
}) => {
  const diff = compareSemesters(baseEvents, targetEvents)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Multi-Semester Schedule Comparison"
      description={`Comparing ${baseSemesterLabel} against ${targetSemesterLabel}`}
      footer={
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close Comparison
        </Button>
      }
    >
      <div className="space-y-4 text-xs" data-testid="semester-comparison-modal">
        <div className="grid grid-cols-3 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 text-center">
          <div>
            <p className="text-slate-400">Room Reassignments</p>
            <p className="text-lg font-extrabold text-blue-700">
              {diff.roomChangedCourses.length}
            </p>
          </div>
          <div>
            <p className="text-slate-400">Time Slot Shifts</p>
            <p className="text-lg font-extrabold text-amber-600">
              {diff.slotChangedCourses.length}
            </p>
          </div>
          <div>
            <p className="text-slate-400">Unchanged Courses</p>
            <p className="text-lg font-extrabold text-emerald-600">
              {diff.unchangedCount}
            </p>
          </div>
        </div>

        {diff.roomChangedCourses.length > 0 && (
          <div className="space-y-2">
            <h5 className="font-bold text-slate-700 uppercase tracking-wider">
              Room Changes
            </h5>
            {diff.roomChangedCourses.map((c) => (
              <div
                key={`room-${c.course_code}`}
                className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200 bg-white"
              >
                <div>
                  <span className="font-bold text-slate-800">{c.course_code}</span>
                  <span className="text-slate-500 ml-1.5">{c.course_name}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant="neutral">{c.oldRoom}</Badge>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                  <Badge variant="info">{c.newRoom}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}

        {diff.slotChangedCourses.length > 0 && (
          <div className="space-y-2">
            <h5 className="font-bold text-slate-700 uppercase tracking-wider">
              Time Slot Shifts
            </h5>
            {diff.slotChangedCourses.map((c) => (
              <div
                key={`slot-${c.course_code}`}
                className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200 bg-white"
              >
                <div>
                  <span className="font-bold text-slate-800">{c.course_code}</span>
                  <span className="text-slate-500 ml-1.5">{c.course_name}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant="neutral">{c.oldSlot}</Badge>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                  <Badge variant="warning">{c.newSlot}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  )
}

export default SemesterComparisonModal
