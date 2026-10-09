import React, { useState } from 'react'
import { Clock } from 'lucide-react'
import { Alert, Card, CardHeader, CardTitle, CardContent, Button, Select } from '../components/ui'

export const PreferencesPage: React.FC = () => {
  const [selectedInstructor, setSelectedInstructor] = useState('1')
  const [selectedDays, setSelectedDays] = useState<string[]>(['Monday (M)', 'Wednesday (W)'])

  const instructors = [
    { value: '1', label: 'Dr. Yugyung Lee (Computer Science)' },
    { value: '2', label: 'Dr. Praveen Rao (Computer Science)' },
    { value: '3', label: 'Dr. Ghulam Rasool (Electrical & Computer Eng)' },
    { value: '4', label: 'Dr. Liana Sega (Mathematics)' },
  ]

  const dayOptions = [
    'Monday (M)',
    'Tuesday (T)',
    'Wednesday (W)',
    'Thursday (R)',
    'Friday (F)',
  ]

  const timeSlots = [
    '08:00 - 09:15',
    '09:30 - 10:45',
    '11:00 - 12:15',
    '13:00 - 14:15',
    '14:30 - 15:45',
    '16:00 - 17:15',
  ]

  const toggleDay = (day: string) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Instructor Preferences</h1>
        <p className="text-sm text-slate-500 mt-1">
          Specify teaching day patterns, time slot availability, and classroom layout needs.
        </p>
      </div>

      <Alert variant="info" title="Sprint 0 Architecture Contract">
        This form interface demonstrates component integration with the design system. In Sprint 1,
        submitting this form will call{' '}
        <code className="bg-blue-100 px-1 py-0.5 rounded font-mono">POST /api/v1/preferences</code>{' '}
        via <code className="bg-blue-100 px-1 py-0.5 rounded font-mono">preferenceService</code>.
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Teaching Availability Form</CardTitle>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="max-w-md">
            <Select
              label="Select Instructor"
              options={instructors}
              value={selectedInstructor}
              onChange={(e) => setSelectedInstructor(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">Preferred Days</label>
            <div className="flex flex-wrap gap-2">
              {dayOptions.map((day) => {
                const isSelected = selectedDays.includes(day)
                return (
                  <Button
                    key={day}
                    type="button"
                    variant={isSelected ? 'primary' : 'outline'}
                    size="sm"
                    onClick={() => toggleDay(day)}
                  >
                    {day}
                  </Button>
                )
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">Preferred Time Slots</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              {timeSlots.map((slot) => (
                <div
                  key={slot}
                  className="p-2.5 rounded-xl border border-slate-200 text-xs text-slate-600 bg-slate-50 flex items-center space-x-2"
                >
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{slot}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 flex items-center space-x-3">
            <Button variant="primary">
              Save Preferences
            </Button>
            <Button variant="secondary">
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default PreferencesPage
