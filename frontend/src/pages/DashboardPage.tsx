import React, { useEffect, useState } from 'react'
import { CalendarDays, Users, School, Sparkles, ArrowRight, Layers } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '../components/ui'
import { EditRequestQueue } from '../components/admin/EditRequestQueue'
import { useAuth } from '../context/AuthContext'
import { courseService } from '../services/courseService'
import { roomService } from '../services/roomService'
import { instructorService } from '../services/instructorService'

export const DashboardPage: React.FC = () => {
  const { user } = useAuth()
  const isCoordinator = (user?.role ?? 'coordinator') === 'coordinator'

  const [facultyCount, setFacultyCount] = useState<string>('20')
  const [courseCount, setCourseCount] = useState<string>('40')
  const [roomCount, setRoomCount] = useState<string>('12')

  useEffect(() => {
    let active = true
    Promise.all([
      courseService.getCourses(),
      roomService.getRooms(),
      instructorService.getInstructors(),
    ]).then(([courses, rooms, instructors]) => {
      if (!active) return
      setCourseCount(String(courses.length))
      setRoomCount(String(rooms.length))
      setFacultyCount(String(instructors.length))
    })
    return () => {
      active = false
    }
  }, [])

  const stats = [
    { label: 'Total Faculty', value: facultyCount, sub: 'CS, ECE, Math, Biology, Chem', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Active Courses', value: courseCount, sub: 'Undergrad & Graduate Courses', icon: CalendarDays, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Classrooms & Labs', value: roomCount, sub: 'RH, FH, MN, SCB Buildings', icon: School, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Semesters Covered', value: '6 Terms', sub: 'Fall 2024 to Spring 2027', icon: Sparkles, color: 'text-amber-600', bg: 'bg-amber-50' },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {isCoordinator ? 'Coordinator Dashboard' : 'Faculty Instructor Dashboard'}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            OptiSched constraint satisfaction engine overview and active semester metrics.
          </p>
        </div>

        {isCoordinator && (
          <Link to="/courses">
            <Button
              variant="gold"
              size="sm"
              leftIcon={<Layers className="w-4 h-4" />}
              data-testid="dashboard-manage-courses-btn"
            >
              Manage Courses & Sections
            </Button>
          </Link>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((s, idx) => {
          const Icon = s.icon
          return (
            <Card key={idx} hoverable className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{s.label}</span>
                <div className={`p-2 rounded-xl ${s.bg} ${s.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-slate-800">{s.value}</div>
              <div className="text-xs text-slate-500">{s.sub}</div>
            </Card>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card hoverable className="lg:col-span-2">
          <CardHeader>
            <CardTitle>OptiSched Engine & Role Workspace</CardTitle>
            <Badge variant="success" dot>
              Active
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              The Google OR-Tools CP-SAT core solver is verified against 25/25 automated test cases spanning 6 consecutive academic terms. FastAPI endpoints enforce role-based session gates for Course Coordinators and Faculty Instructors.
            </p>
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <Link to="/schedule">
                <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
                  View Master Schedule
                </Button>
              </Link>
              <Link to="/preferences">
                <Button variant="secondary" size="sm">
                  Preference Setup
                </Button>
              </Link>
              {isCoordinator && (
                <Link to="/courses">
                  <Button variant="outline" size="sm">
                    Manage Courses & Sections
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>

        <Card hoverable>
          <CardHeader>
            <CardTitle>Team Ownership</CardTitle>
            <Badge variant="gold">CS 5551</Badge>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3 text-xs">
              <li className="flex justify-between pb-2 border-b border-slate-100">
                <span className="font-semibold text-slate-700">Joe (Coordinator)</span>
                <span className="text-slate-500">OR-Tools Engine</span>
              </li>
              <li className="flex justify-between pb-2 border-b border-slate-100">
                <span className="font-semibold text-slate-700">Tony (Backend)</span>
                <span className="text-slate-500">FastAPI & SQLModel</span>
              </li>
              <li className="flex justify-between pb-2 border-b border-slate-100">
                <span className="font-semibold text-slate-700">Tina (Frontend)</span>
                <span className="text-slate-500">Shell & Forms</span>
              </li>
              <li className="flex justify-between">
                <span className="font-semibold text-slate-700">Sal (Frontend)</span>
                <span className="text-slate-500">Matrix & API Client</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <EditRequestQueue />
    </div>
  )
}

export default DashboardPage
