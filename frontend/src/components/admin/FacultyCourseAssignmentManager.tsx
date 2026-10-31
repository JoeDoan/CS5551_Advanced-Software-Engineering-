import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Check, GraduationCap, Search, UserCheck } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Select,
} from '../ui'
import { Toast } from '../common/Toast'
import { courseService } from '../../services/courseService'
import { DEFAULT_INSTRUCTORS, instructorService } from '../../services/instructorService'
import { courseAssignmentService } from '../../services/courseAssignmentService'
import { Course, CourseAssignment, InstructorSummary } from '../../types/api'
import {
  ACADEMIC_SEMESTERS,
  CURRENT_SEMESTER_ID,
  CourseLevel,
  STANDARD_DEPARTMENTS,
  formatCourseLevel,
  getCourseLevel,
} from '../../utils/academicDomain'

export interface FacultyCourseAssignmentManagerProps {
  catalogVersion?: number
  onAssignmentsChanged?: () => void
}

const SEMESTER_SELECT_OPTIONS = ACADEMIC_SEMESTERS.map((s) => ({
  value: String(s.id),
  label: s.isActive ? `Semester ${s.id} (${s.name} — Current)` : `Semester ${s.id} (${s.name})`,
}))

const LEVEL_SELECT_OPTIONS = [
  { value: 'ALL', label: 'All Levels' },
  { value: 'undergraduate', label: 'Undergraduate (100-499 / 1000-4999)' },
  { value: 'graduate', label: 'Graduate (500+ / 5000+)' },
]

export const FacultyCourseAssignmentManager: React.FC<FacultyCourseAssignmentManagerProps> = ({
  catalogVersion = 0,
  onAssignmentsChanged,
}) => {
  const [selectedSemester, setSelectedSemester] = useState<number>(CURRENT_SEMESTER_ID)
  const [instructors, setInstructors] = useState<InstructorSummary[]>(DEFAULT_INSTRUCTORS)
  const [selectedInstructorId, setSelectedInstructorId] = useState<string>(
    String(DEFAULT_INSTRUCTORS[0]?.id ?? 1)
  )
  const [courses, setCourses] = useState<Course[]>([])
  const [semesterAssignments, setSemesterAssignments] = useState<CourseAssignment[]>([])
  const [selectedCourseIds, setSelectedCourseIds] = useState<number[]>([])

  const [deptFilter, setDeptFilter] = useState<string>('ALL')
  const [levelFilter, setLevelFilter] = useState<'ALL' | CourseLevel>('ALL')
  const [courseSearch, setCourseSearch] = useState<string>('')
  const [saving, setSaving] = useState<boolean>(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const hasDirtySelectionRef = useRef<boolean>(false)

  const loadCatalogs = useCallback(async () => {
    const [loadedCourses, loadedInstructors] = await Promise.all([
      courseService.getCourses(),
      instructorService.getInstructors(),
    ])
    setCourses(loadedCourses)
    setInstructors(loadedInstructors)
    setSelectedInstructorId((prev) => {
      if (loadedInstructors.some((i) => String(i.id) === prev)) {
        return prev
      }
      return String(loadedInstructors[0]?.id ?? 1)
    })
  }, [])

  useEffect(() => {
    loadCatalogs()
  }, [loadCatalogs, catalogVersion])

  useEffect(() => {
    let active = true
    courseAssignmentService
      .getAssignments({ semester_id: selectedSemester })
      .then((items) => {
        if (!active) return
        setSemesterAssignments(items)
      })
      .catch(() => {
        if (active) setSemesterAssignments([])
      })
    return () => {
      active = false
    }
  }, [selectedSemester])

  useEffect(() => {
    if (hasDirtySelectionRef.current) return
    const targetUserId = Number(selectedInstructorId)
    const assignedIds = semesterAssignments
      .filter((a) => a.user_id === targetUserId)
      .map((a) => a.course_id)
    setSelectedCourseIds(assignedIds)
  }, [semesterAssignments, selectedInstructorId])

  const departmentOptions = useMemo(() => {
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

  const filteredCourses = useMemo(() => {
    const query = courseSearch.trim().toLowerCase()
    return courses.filter((course) => {
      if (deptFilter !== 'ALL' && course.department.trim().toUpperCase() !== deptFilter) {
        return false
      }
      if (levelFilter !== 'ALL' && getCourseLevel(course.course_code) !== levelFilter) {
        return false
      }
      if (
        query &&
        !course.course_code.toLowerCase().includes(query) &&
        !course.course_name.toLowerCase().includes(query)
      ) {
        return false
      }
      return true
    })
  }, [courses, deptFilter, levelFilter, courseSearch])

  const courseById = useMemo(() => {
    const map = new Map<number, Course>()
    for (const c of courses) {
      map.set(c.id, c)
    }
    return map
  }, [courses])

  const activeInstructor = useMemo(
    () => instructors.find((i) => String(i.id) === selectedInstructorId),
    [instructors, selectedInstructorId]
  )

  const groupedSemesterAssignments = useMemo(() => {
    const byInstructor = new Map<
      number,
      {
        user_id: number
        instructor_name: string
        instructor_department: string
        items: CourseAssignment[]
      }
    >()
    for (const item of semesterAssignments) {
      const existing = byInstructor.get(item.user_id)
      if (existing) {
        existing.items.push(item)
      } else {
        byInstructor.set(item.user_id, {
          user_id: item.user_id,
          instructor_name: item.instructor_name,
          instructor_department: item.instructor_department,
          items: [item],
        })
      }
    }
    return Array.from(byInstructor.values()).sort((a, b) =>
      a.instructor_name.localeCompare(b.instructor_name)
    )
  }, [semesterAssignments])

  const toggleCourseSelection = (courseId: number) => {
    hasDirtySelectionRef.current = true
    setSelectedCourseIds((prev) =>
      prev.includes(courseId) ? prev.filter((id) => id !== courseId) : [...prev, courseId]
    )
  }

  const handleSaveAssignments = async () => {
    const userId = Number(selectedInstructorId)
    if (!userId) return

    setSaving(true)
    try {
      await courseAssignmentService.setInstructorAssignments({
        semester_id: selectedSemester,
        user_id: userId,
        course_ids: selectedCourseIds,
      })
      const refreshed = await courseAssignmentService.getAssignments({
        semester_id: selectedSemester,
      })
      hasDirtySelectionRef.current = false
      setSemesterAssignments(refreshed)
      onAssignmentsChanged?.()
      const instructorLabel = activeInstructor?.full_name ?? `Instructor #${userId}`
      setToast({
        type: 'success',
        message: `Saved ${selectedCourseIds.length} course assignment(s) for ${instructorLabel}`,
      })
    } catch (err) {
      setToast({
        type: 'error',
        message: (err as Error).message || 'Failed to save faculty course assignments.',
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card data-testid="faculty-assignment-manager">
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
            <UserCheck className="w-4 h-4" />
          </div>
          <div>
            <CardTitle>Faculty Course Assignments</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">
              Assign undergraduate and graduate courses to faculty instructors by department and
              course level
            </p>
          </div>
        </div>
        <Badge variant="info" data-testid="semester-assignment-count-badge">
          {semesterAssignments.length} Active Assignment
          {semesterAssignments.length === 1 ? '' : 's'}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <Select
            label="Academic Semester"
            value={String(selectedSemester)}
            onChange={(e) => {
              hasDirtySelectionRef.current = false
              setSelectedSemester(Number(e.target.value))
            }}
            options={SEMESTER_SELECT_OPTIONS}
            data-testid="assignment-semester-select"
          />

          <Select
            label="Faculty Instructor"
            value={selectedInstructorId}
            onChange={(e) => {
              hasDirtySelectionRef.current = false
              setSelectedInstructorId(e.target.value)
            }}
            options={instructors.map((inst) => ({
              value: String(inst.id),
              label: `${inst.full_name} (${inst.department})`,
            }))}
            data-testid="assignment-instructor-select"
          />

          <Select
            label="Department Filter"
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            options={departmentOptions}
            data-testid="assignment-dept-filter"
          />

          <Select
            label="Course Level Filter"
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value as 'ALL' | CourseLevel)}
            options={LEVEL_SELECT_OPTIONS}
            data-testid="assignment-level-filter"
          />

          <Input
            label="Course Search"
            placeholder="Filter by code or title..."
            value={courseSearch}
            onChange={(e) => setCourseSearch(e.target.value)}
            leftIcon={<Search className="w-4 h-4" />}
            data-testid="assignment-course-search"
          />
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="font-semibold text-slate-700">
              Select Courses for {activeInstructor?.full_name ?? 'Selected Instructor'} (
              {filteredCourses.length} matching filter)
            </span>
            <span className="text-blue-700 font-semibold">
              {selectedCourseIds.length} course{selectedCourseIds.length === 1 ? '' : 's'} selected
            </span>
          </div>

          {filteredCourses.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-4 text-xs text-slate-500 text-center">
              No catalog courses match the active Department and Course Level filters.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-72 overflow-y-auto pr-1">
              {filteredCourses.map((course) => {
                const isSelected = selectedCourseIds.includes(course.id)
                const level = getCourseLevel(course.course_code)
                return (
                  <button
                    key={course.id}
                    type="button"
                    data-testid={`assign-course-toggle-${course.id}`}
                    aria-pressed={isSelected}
                    onClick={() => toggleCourseSelection(course.id)}
                    className={`p-3 rounded-xl border text-left text-xs transition-all cursor-pointer focus:outline-none flex flex-col justify-between gap-2 ${
                      isSelected
                        ? 'bg-blue-50 border-blue-600 ring-2 ring-blue-500/20'
                        : 'bg-slate-50/70 border-slate-200 hover:bg-slate-100/80 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-slate-900">
                        {`${course.course_code} — ${course.course_name}`}
                      </span>
                      <span
                        className={`w-4 h-4 rounded flex items-center justify-center border shrink-0 mt-0.5 ${
                          isSelected
                            ? 'bg-blue-600 border-blue-600 text-white'
                            : 'border-slate-300 bg-white'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3" />}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant="neutral">{course.department}</Badge>
                      <Badge variant={level === 'graduate' ? 'gold' : 'info'}>
                        {formatCourseLevel(level)}
                      </Badge>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="font-semibold text-slate-700 mr-1">Assigned Load:</span>
            {selectedCourseIds.length === 0 ? (
              <span className="text-slate-500">
                No courses selected for {activeInstructor?.full_name ?? 'this instructor'}.
              </span>
            ) : (
              selectedCourseIds.map((cid) => {
                const c = courseById.get(cid)
                const code = c?.course_code ?? `Course #${cid}`
                const level = getCourseLevel(code)
                return (
                  <Badge key={cid} variant={level === 'graduate' ? 'gold' : 'info'}>
                    {`${code} (${formatCourseLevel(level)})`}
                  </Badge>
                )
              })
            )}
          </div>

          <Button
            variant="primary"
            size="sm"
            isLoading={saving}
            leftIcon={<Check className="w-4 h-4" />}
            onClick={handleSaveAssignments}
            data-testid="save-instructor-assignments-btn"
          >
            Save Instructor Assignments
          </Button>
        </div>

        <div className="space-y-2" data-testid="semester-assignments-summary">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-700">
            <GraduationCap className="w-4 h-4 text-indigo-600" />
            <span>Semester Teaching Assignments Summary</span>
          </div>
          {groupedSemesterAssignments.length === 0 ? (
            <p className="text-xs text-slate-500">
              No explicit faculty course assignments saved for this semester yet.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {groupedSemesterAssignments.map((group) => (
                <div
                  key={group.user_id}
                  data-testid={`instructor-assignment-summary-${group.user_id}`}
                  className="p-3 rounded-xl border border-slate-200 bg-white flex flex-col gap-2 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-800">
                      {`${group.instructor_name}${
                        group.instructor_department ? ` (${group.instructor_department})` : ''
                      }`}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        hasDirtySelectionRef.current = false
                        setSelectedInstructorId(String(group.user_id))
                      }}
                      className="text-[11px] font-semibold text-blue-600 hover:text-blue-800"
                    >
                      Edit Load
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {group.items.map((item) => (
                      <Badge
                        key={item.id}
                        variant={item.course_level === 'graduate' ? 'gold' : 'info'}
                      >
                        {`${item.course_code} · ${formatCourseLevel(item.course_level)}`}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>

      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}
    </Card>
  )
}

export default FacultyCourseAssignmentManager
