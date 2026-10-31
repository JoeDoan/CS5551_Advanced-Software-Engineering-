import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Plus, Edit2, Trash2, Search } from 'lucide-react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Modal,
  Select,
} from '../ui'
import { Toast } from '../common/Toast'
import { courseService } from '../../services/courseService'
import { roomService } from '../../services/roomService'
import { instructorService } from '../../services/instructorService'
import { timeSlotService } from '../../services/timeSlotService'
import { scheduleService } from '../../services/scheduleService'
import {
  Course,
  InstructorSummary,
  Room,
  ScheduleEvent,
  TimeSlot,
} from '../../types/api'
import {
  ACADEMIC_SEMESTERS,
  CURRENT_SEMESTER_ID,
  CourseLevel,
  STANDARD_DEPARTMENTS,
  formatCourseLevel,
  formatRoomWithBuilding,
  getCourseLevel,
} from '../../utils/academicDomain'

const SEMESTERS = ACADEMIC_SEMESTERS.map((s) => ({
  value: String(s.id),
  label: s.isActive ? `Semester ${s.id} (${s.name} — Current)` : `Semester ${s.id} (${s.name})`,
}))

export interface SectionManagerProps {
  preselectedCourse?: Course | null
  onClearPreselectedCourse?: () => void
  catalogVersion?: number
  roomsVersion?: number
}

export const SectionManager: React.FC<SectionManagerProps> = ({
  preselectedCourse,
  onClearPreselectedCourse,
  catalogVersion = 0,
  roomsVersion = 0,
}) => {
  const [selectedSemester, setSelectedSemester] = useState<number>(CURRENT_SEMESTER_ID)
  const [schedules, setSchedules] = useState<ScheduleEvent[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [instructors, setInstructors] = useState<InstructorSummary[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([])
  const [search, setSearch] = useState('')

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingSection, setEditingSection] = useState<ScheduleEvent | null>(null)
  const [modalError, setModalError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const [modalDeptFilter, setModalDeptFilter] = useState<string>('ALL')
  const [modalLevelFilter, setModalLevelFilter] = useState<'ALL' | CourseLevel>('ALL')
  const [courseId, setCourseId] = useState<string>('')
  const [instructorId, setInstructorId] = useState<string>('')
  const [roomId, setRoomId] = useState<string>('')
  const [timeSlotId, setTimeSlotId] = useState<string>('')

  const loadReferenceCatalogs = useCallback(async () => {
    const [loadedCourses, loadedInstructors, loadedRooms, loadedSlots] = await Promise.all([
      courseService.getCourses(),
      instructorService.getInstructors(),
      roomService.getRooms(),
      timeSlotService.getAllTimeSlots(),
    ])
    setCourses(loadedCourses)
    setInstructors(loadedInstructors)
    setRooms(loadedRooms)
    setTimeSlots(loadedSlots)
  }, [])

  useEffect(() => {
    loadReferenceCatalogs()
  }, [loadReferenceCatalogs, catalogVersion, roomsVersion])

  useEffect(() => {
    let active = true
    scheduleService.getBySemester(selectedSemester).then((events) => {
      if (active) {
        setSchedules(events)
      }
    })
    return () => {
      active = false
    }
  }, [selectedSemester])

  useEffect(() => {
    if (!preselectedCourse) return
    setCourses((prev) =>
      prev.some((c) => c.id === preselectedCourse.id) ? prev : [...prev, preselectedCourse]
    )
    setEditingSection(null)
    setModalError(null)
    setModalDeptFilter('ALL')
    setModalLevelFilter('ALL')
    setCourseId(String(preselectedCourse.id))
    setInstructorId((prev) => prev || String(instructors[0]?.id ?? 1))
    setRoomId((prev) => {
      if (preselectedCourse.requires_lab) {
        const labRoom = rooms.find((r) => r.room_type.toLowerCase() === 'lab')
        if (labRoom) return String(labRoom.id)
      }
      return prev || String(rooms[0]?.id ?? 1)
    })
    setTimeSlotId((prev) => prev || String(timeSlots[0]?.id ?? 1))
    setIsModalOpen(true)
    onClearPreselectedCourse?.()
  }, [preselectedCourse, instructors, rooms, timeSlots, onClearPreselectedCourse])

  const openAssignModal = () => {
    setEditingSection(null)
    setModalError(null)
    setModalDeptFilter('ALL')
    setModalLevelFilter('ALL')
    setCourseId(String(courses[0]?.id ?? 1))
    setInstructorId(String(instructors[0]?.id ?? 1))
    setRoomId(String(rooms[0]?.id ?? 1))
    setTimeSlotId(String(timeSlots[0]?.id ?? 1))
    setIsModalOpen(true)
  }

  const openEditModal = (section: ScheduleEvent) => {
    setEditingSection(section)
    setModalError(null)
    setModalDeptFilter('ALL')
    setModalLevelFilter('ALL')
    setCourseId(String(section.course_id))
    setInstructorId(
      String(section.user_id ?? section.instructor_id ?? instructors[0]?.id ?? 1)
    )
    const matchedRoom =
      rooms.find((r) => r.id === section.room_id) ??
      rooms.find((r) => r.room_number === section.room_number)
    setRoomId(String(matchedRoom?.id ?? rooms[0]?.id ?? 1))

    const matchedSlot =
      timeSlots.find((s) => s.id === section.time_slot_id) ??
      timeSlots.find(
        (s) =>
          s.day_pattern === section.day_pattern &&
          s.start_time === section.start_time
      )
    setTimeSlotId(String(matchedSlot?.id ?? timeSlots[0]?.id ?? 1))
    setIsModalOpen(true)
  }

  const handleSaveSection = async () => {
    setModalError(null)
    setSaving(true)
    try {
      if (editingSection) {
        const updated = await scheduleService.updateSchedule(editingSection.id, {
          user_id: Number(instructorId),
          room_id: Number(roomId),
          time_slot_id: Number(timeSlotId),
        })
        setSchedules((prev) => prev.map((s) => (s.id === editingSection.id ? updated : s)))
        setToast({
          type: 'success',
          message: `Updated section ${updated.course_code} (${updated.room_number})`,
        })
      } else {
        const created = await scheduleService.createSchedule({
          semester_id: selectedSemester,
          course_id: Number(courseId),
          user_id: Number(instructorId),
          room_id: Number(roomId),
          time_slot_id: Number(timeSlotId),
          status: 'confirmed',
        })
        setSchedules((prev) => [...prev, created])
        setToast({
          type: 'success',
          message: `Scheduled ${created.course_code} in ${created.room_number}`,
        })
      }
      setIsModalOpen(false)
    } catch (err) {
      const msg = (err as Error).message || 'Conflict detected while saving section.'
      setModalError(msg)
      setToast({ type: 'error', message: msg })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteSection = async (section: ScheduleEvent) => {
    try {
      await scheduleService.deleteSchedule(section.id)
      setSchedules((prev) => prev.filter((s) => s.id !== section.id))
      setToast({
        type: 'success',
        message: `Unscheduled ${section.course_code} (${section.day_pattern} ${section.start_time})`,
      })
    } catch (err) {
      setToast({
        type: 'error',
        message: (err as Error).message || 'Failed to delete scheduled section.',
      })
    }
  }

  const modalDepartmentOptions = useMemo(() => {
    const seen = new Set<string>(STANDARD_DEPARTMENTS)
    for (const c of courses) {
      const normalized = c.department?.trim().toUpperCase()
      if (normalized) seen.add(normalized)
    }
    return [
      { value: 'ALL', label: 'All Departments' },
      ...Array.from(seen).map((dept) => ({
        value: dept,
        label: dept,
      })),
    ]
  }, [courses])

  const filterModalCourses = useCallback(
    (dept: string, level: 'ALL' | CourseLevel): Course[] => {
      return courses.filter((c) => {
        if (dept !== 'ALL' && c.department.trim().toUpperCase() !== dept) {
          return false
        }
        if (level !== 'ALL' && getCourseLevel(c.course_code) !== level) {
          return false
        }
        return true
      })
    },
    [courses]
  )

  const modalCourseList = useMemo(() => {
    if (editingSection) return courses
    const matching = filterModalCourses(modalDeptFilter, modalLevelFilter)
    if (matching.length > 0) return matching
    const selected = courses.find((c) => String(c.id) === courseId)
    return selected ? [selected] : []
  }, [editingSection, courses, filterModalCourses, modalDeptFilter, modalLevelFilter, courseId])

  const handleModalDeptFilterChange = (nextDept: string) => {
    setModalDeptFilter(nextDept)
    const matching = filterModalCourses(nextDept, modalLevelFilter)
    if (matching.length > 0 && !matching.some((c) => String(c.id) === courseId)) {
      setCourseId(String(matching[0].id))
    }
  }

  const handleModalLevelFilterChange = (nextLevel: 'ALL' | CourseLevel) => {
    setModalLevelFilter(nextLevel)
    const matching = filterModalCourses(modalDeptFilter, nextLevel)
    if (matching.length > 0 && !matching.some((c) => String(c.id) === courseId)) {
      setCourseId(String(matching[0].id))
    }
  }

  useEffect(() => {
    if (!isModalOpen || editingSection) return
    if (modalCourseList.length > 0 && !modalCourseList.some((c) => String(c.id) === courseId)) {
      setCourseId(String(modalCourseList[0].id))
    }
    if (instructors.length > 0 && !instructors.some((i) => String(i.id) === instructorId)) {
      setInstructorId(String(instructors[0].id))
    }
    if (rooms.length > 0 && !rooms.some((r) => String(r.id) === roomId)) {
      setRoomId(String(rooms[0].id))
    }
    if (timeSlots.length > 0 && !timeSlots.some((s) => String(s.id) === timeSlotId)) {
      setTimeSlotId(String(timeSlots[0].id))
    }
  }, [
    isModalOpen,
    editingSection,
    modalCourseList,
    courseId,
    instructors,
    instructorId,
    rooms,
    roomId,
    timeSlots,
    timeSlotId,
  ])

  const filteredSchedules = schedules.filter((s) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      (s.course_code || '').toLowerCase().includes(q) ||
      (s.course_name || '').toLowerCase().includes(q) ||
      (s.instructor_name || '').toLowerCase().includes(q) ||
      (s.room_number || '').toLowerCase().includes(q) ||
      (s.day_pattern || '').toLowerCase().includes(q)
    )
  })

  return (
    <Card data-testid="section-manager">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2.5">
          <div>
            <CardTitle>Scheduled Course Sections</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Assign courses to instructors, classrooms, and time slots with live conflict checks
            </p>
          </div>
          <Badge variant="gold" data-testid="section-count-badge">
            {schedules.length} Scheduled Sections
          </Badge>
        </div>
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={openAssignModal}
          data-testid="add-section-btn"
        >
          Assign New Section
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="w-full sm:w-64">
            <Select
              value={String(selectedSemester)}
              onChange={(e) => setSelectedSemester(Number(e.target.value))}
              options={SEMESTERS}
              data-testid="section-semester-select"
            />
          </div>
          <div className="flex-1">
            <Input
              placeholder="Search scheduled sections by course, instructor, or room..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
              data-testid="section-search-input"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase">
                <th className="py-2.5 px-3">Course</th>
                <th className="py-2.5 px-3">Instructor</th>
                <th className="py-2.5 px-3">Classroom</th>
                <th className="py-2.5 px-3">Schedule Slot</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredSchedules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-500">
                    No scheduled sections match the current filter.
                  </td>
                </tr>
              ) : (
                filteredSchedules.map((section) => (
                  <tr key={section.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-800">{section.course_code}</div>
                      <div className="text-[11px] text-slate-500">{section.course_name}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700">{section.instructor_name}</td>
                    <td className="py-2.5 px-3">
                      <Badge variant="neutral">{section.room_number}</Badge>
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-700">
                      {section.day_pattern} {section.start_time}-{section.end_time}
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant="success" dot>
                        {section.status || 'confirmed'}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-1 whitespace-nowrap">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEditModal(section)}
                        data-testid={`edit-section-${section.id}`}
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteSection(section)}
                        data-testid={`delete-section-${section.id}`}
                      >
                        <Trash2 className="w-3.5 h-3.5 text-red-600" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingSection ? `Edit Section (${editingSection.course_code})` : 'Assign New Section'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={saving}
              onClick={handleSaveSection}
              data-testid="save-section-btn"
            >
              {editingSection ? 'Update Section' : 'Schedule Section'}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {modalError && (
            <Alert variant="danger" title="Scheduling Constraint Conflict">
              {modalError}
            </Alert>
          )}

          {!editingSection && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Select
                label="Department Filter"
                value={modalDeptFilter}
                onChange={(e) => handleModalDeptFilterChange(e.target.value)}
                options={modalDepartmentOptions}
                data-testid="modal-section-dept-filter"
              />
              <Select
                label="Course Level"
                value={modalLevelFilter}
                onChange={(e) =>
                  handleModalLevelFilterChange(e.target.value as 'ALL' | CourseLevel)
                }
                options={[
                  { value: 'ALL', label: 'All Levels' },
                  { value: 'undergraduate', label: 'Undergraduate' },
                  { value: 'graduate', label: 'Graduate' },
                ]}
                data-testid="modal-section-level-filter"
              />
            </div>
          )}

          <Select
            label="Course"
            value={courseId}
            disabled={Boolean(editingSection)}
            onChange={(e) => setCourseId(e.target.value)}
            options={modalCourseList.map((c) => {
              const levelLabel = formatCourseLevel(getCourseLevel(c.course_code))
              return {
                value: String(c.id),
                label: `${c.course_code} [${levelLabel}]: ${c.course_name} (${
                  c.expected_enrollment
                } seats${c.requires_lab ? ', Lab' : ''})`,
              }
            })}
            data-testid="modal-section-course"
          />

          <Select
            label="Faculty Instructor"
            value={instructorId}
            onChange={(e) => setInstructorId(e.target.value)}
            options={instructors.map((inst) => ({
              value: String(inst.id),
              label: `${inst.full_name} (${inst.department})`,
            }))}
            data-testid="modal-section-instructor"
          />

          <Select
            label="Classroom or Laboratory"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            options={rooms.map((r) => ({
              value: String(r.id),
              label: `${formatRoomWithBuilding(r)} (${r.capacity} seats, ${r.room_type})`,
            }))}
            data-testid="modal-section-room"
          />

          <Select
            label="Time Slot"
            value={timeSlotId}
            onChange={(e) => setTimeSlotId(e.target.value)}
            options={timeSlots.map((slot) => ({
              value: String(slot.id),
              label: `${slot.day_pattern} ${slot.start_time}-${slot.end_time}`,
            }))}
            data-testid="modal-section-timeslot"
          />
        </div>
      </Modal>

      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}
    </Card>
  )
}

export default SectionManager
