import React, { useEffect, useState } from 'react'
import { Plus, Trash2, Edit2, Search } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Select, Badge, Modal } from '../ui'
import { Toast } from '../common/Toast'
import { courseService } from '../../services/courseService'
import { Course } from '../../types/api'

export const CourseManager: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([])
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('ALL')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCourse, setEditingCourse] = useState<Course | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const [courseCode, setCourseCode] = useState('')
  const [courseName, setCourseName] = useState('')
  const [department, setDepartment] = useState('CS')
  const [credits, setCredits] = useState('3')
  const [enrollment, setEnrollment] = useState('40')
  const [requiresLab, setRequiresLab] = useState(false)

  useEffect(() => {
    courseService.getCourses().then(setCourses)
  }, [])

  const openAddModal = () => {
    setEditingCourse(null)
    setCourseCode('')
    setCourseName('')
    setDepartment('CS')
    setCredits('3')
    setEnrollment('40')
    setRequiresLab(false)
    setIsModalOpen(true)
  }

  const openEditModal = (course: Course) => {
    setEditingCourse(course)
    setCourseCode(course.course_code)
    setCourseName(course.course_name)
    setDepartment(course.department)
    setCredits(String(course.credits))
    setEnrollment(String(course.expected_enrollment))
    setRequiresLab(course.requires_lab)
    setIsModalOpen(true)
  }

  const handleSaveCourse = async () => {
    if (!courseCode.trim() || !courseName.trim()) {
      setToast({ type: 'error', message: 'Course code and name are required.' })
      return
    }
    const payload = {
      course_code: courseCode.trim(),
      course_name: courseName.trim(),
      department,
      credits: Number(credits) || 3,
      expected_enrollment: Number(enrollment) || 30,
      requires_lab: requiresLab,
    }
    if (editingCourse) {
      const updated = await courseService.updateCourse(editingCourse.id, payload)
      setCourses((prev) => prev.map((c) => (c.id === editingCourse.id ? updated : c)))
      setToast({ type: 'success', message: `Updated ${updated.course_code}` })
    } else {
      const created = await courseService.createCourse(payload)
      setCourses((prev) => [...prev, created])
      setToast({ type: 'success', message: `Added ${created.course_code}` })
    }
    setIsModalOpen(false)
  }

  const handleDeleteCourse = async (course: Course) => {
    await courseService.deleteCourse(course.id)
    setCourses((prev) => prev.filter((c) => c.id !== course.id))
    setToast({ type: 'success', message: `Removed ${course.course_code}` })
  }

  const filtered = courses.filter((c) => {
    const matchesDept = deptFilter === 'ALL' || c.department.toUpperCase() === deptFilter
    const q = search.toLowerCase()
    const matchesSearch =
      !q ||
      c.course_code.toLowerCase().includes(q) ||
      c.course_name.toLowerCase().includes(q)
    return matchesDept && matchesSearch
  })

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Course Catalog Manager</CardTitle>
          <p className="text-xs text-slate-500 mt-0.5">Add, edit, or remove academic courses</p>
        </div>
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={openAddModal}
          data-testid="add-course-btn"
        >
          Add Course
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              placeholder="Search course code or title..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
              data-testid="course-search-input"
            />
          </div>
          <div className="w-full sm:w-48">
            <Select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              options={[
                { value: 'ALL', label: 'All Departments' },
                { value: 'CS', label: 'Computer Science' },
                { value: 'ECE', label: 'ECE' },
                { value: 'MATH', label: 'Mathematics' },
                { value: 'CHEM/BIO', label: 'Chem / Bio' },
              ]}
              data-testid="course-dept-filter"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase">
                <th className="py-2.5 px-3">Code</th>
                <th className="py-2.5 px-3">Title</th>
                <th className="py-2.5 px-3">Dept</th>
                <th className="py-2.5 px-3">Enrollment</th>
                <th className="py-2.5 px-3">Lab</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((course) => (
                <tr key={course.id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-semibold text-slate-800">{course.course_code}</td>
                  <td className="py-2.5 px-3 text-slate-600">{course.course_name}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant="info">{course.department}</Badge>
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">{course.expected_enrollment}</td>
                  <td className="py-2.5 px-3">
                    <Badge variant={course.requires_lab ? 'warning' : 'neutral'}>
                      {course.requires_lab ? 'Lab Required' : 'Lecture'}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-right space-x-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => openEditModal(course)}
                      data-testid={`edit-course-${course.id}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteCourse(course)}
                      data-testid={`delete-course-${course.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-600" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingCourse ? 'Edit Course' : 'Add New Course'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSaveCourse} data-testid="save-course-btn">
              Save Course
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Course Code"
            value={courseCode}
            onChange={(e) => setCourseCode(e.target.value)}
            placeholder="e.g. CS 404"
            data-testid="modal-course-code"
          />
          <Input
            label="Course Name"
            value={courseName}
            onChange={(e) => setCourseName(e.target.value)}
            placeholder="e.g. Algorithms"
            data-testid="modal-course-name"
          />
          <Select
            label="Department"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            options={[
              { value: 'CS', label: 'CS' },
              { value: 'ECE', label: 'ECE' },
              { value: 'MATH', label: 'MATH' },
              { value: 'CHEM/BIO', label: 'CHEM/BIO' },
            ]}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Credits"
              type="number"
              value={credits}
              onChange={(e) => setCredits(e.target.value)}
            />
            <Input
              label="Expected Enrollment"
              type="number"
              value={enrollment}
              onChange={(e) => setEnrollment(e.target.value)}
            />
          </div>
          <label className="flex items-center space-x-2 text-xs font-medium text-slate-700 pt-1">
            <input
              type="checkbox"
              checked={requiresLab}
              onChange={(e) => setRequiresLab(e.target.checked)}
            />
            <span>Requires Laboratory Classroom</span>
          </label>
        </div>
      </Modal>

      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}
    </Card>
  )
}

export default CourseManager
