import React, { useState } from 'react'
import { BookOpen, CalendarRange, School, Layers } from 'lucide-react'
import { CourseManager } from '../components/admin/CourseManager'
import { SectionManager } from '../components/admin/SectionManager'
import { RoomManager } from '../components/admin/RoomManager'
import { Alert, Button } from '../components/ui'
import { Course } from '../types/api'

type CatalogTab = 'all' | 'courses' | 'sections' | 'rooms'

export const CatalogManagementPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<CatalogTab>('all')
  const [preselectedCourse, setPreselectedCourse] = useState<Course | null>(null)
  const [catalogVersion, setCatalogVersion] = useState<number>(0)
  const [roomsVersion, setRoomsVersion] = useState<number>(0)

  const handleScheduleCourse = (course: Course) => {
    setPreselectedCourse(course)
    if (activeTab === 'courses' || activeTab === 'rooms') {
      setActiveTab('sections')
    }
  }

  return (
    <div className="space-y-6" data-testid="catalog-management-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Courses, Scheduled Sections & Classrooms
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Coordinator catalog CRUD workspace for academic courses, semester section assignments,
            and facility inventory.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant={activeTab === 'all' ? 'primary' : 'outline'}
            leftIcon={<Layers className="w-4 h-4" />}
            onClick={() => setActiveTab('all')}
            data-testid="tab-all"
          >
            All Workspace
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'courses' ? 'primary' : 'outline'}
            leftIcon={<BookOpen className="w-4 h-4" />}
            onClick={() => setActiveTab('courses')}
            data-testid="tab-courses"
          >
            Courses Catalog
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'sections' ? 'primary' : 'outline'}
            leftIcon={<CalendarRange className="w-4 h-4" />}
            onClick={() => setActiveTab('sections')}
            data-testid="tab-sections"
          >
            Scheduled Sections
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'rooms' ? 'primary' : 'outline'}
            leftIcon={<School className="w-4 h-4" />}
            onClick={() => setActiveTab('rooms')}
            data-testid="tab-rooms"
          >
            Classrooms & Labs
          </Button>
        </div>
      </div>

      <Alert variant="info" title="Coordinator Catalog & Timetable CRUD">
        Create or update courses in the catalog, click <strong>Schedule Section</strong> on any row
        to assign an instructor, classroom, and time slot immediately, or manage room capacities.
      </Alert>

      {(activeTab === 'all' || activeTab === 'courses') && (
        <CourseManager
          onScheduleCourse={handleScheduleCourse}
          onCatalogChanged={() => setCatalogVersion((v) => v + 1)}
        />
      )}

      {(activeTab === 'all' || activeTab === 'sections') && (
        <SectionManager
          preselectedCourse={preselectedCourse}
          onClearPreselectedCourse={() => setPreselectedCourse(null)}
          catalogVersion={catalogVersion}
          roomsVersion={roomsVersion}
        />
      )}

      {(activeTab === 'all' || activeTab === 'rooms') && (
        <RoomManager onRoomsChanged={() => setRoomsVersion((v) => v + 1)} />
      )}
    </div>
  )
}

export default CatalogManagementPage
