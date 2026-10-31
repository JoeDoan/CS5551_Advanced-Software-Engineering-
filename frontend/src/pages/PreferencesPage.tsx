import React, { useEffect, useState } from 'react'
import { Clock, Check } from 'lucide-react'
import { Alert, Card, CardHeader, CardTitle, CardContent, Button, Select } from '../components/ui'
import { Toast } from '../components/common/Toast'
import { preferenceService } from '../services/preferenceService'
import { DEFAULT_INSTRUCTORS, instructorService } from '../services/instructorService'
import { timeSlotService, toSlotKey } from '../services/timeSlotService'
import { InstructorSummary, TimeSlot } from '../types/api'
import { useAuth } from '../context/AuthContext'

const toInstructorOptions = (list: InstructorSummary[]) =>
  list.map((inst) => ({
    value: String(inst.id),
    label: `${inst.full_name} (${inst.department})`,
  }))

export const PreferencesPage: React.FC = () => {
  const { user, isStandaloneFallback } = useAuth()
  const isLockedInstructor =
    !isStandaloneFallback && user?.role === 'instructor' && user.linked_user_id !== null

  const [instructorList, setInstructorList] = useState<InstructorSummary[]>(DEFAULT_INSTRUCTORS)
  const [selectedInstructor, setSelectedInstructor] = useState<string>(() =>
    isLockedInstructor && user?.linked_user_id ? String(user.linked_user_id) : '1'
  )
  const [selectedDays, setSelectedDays] = useState<string[]>(['Monday (M)', 'Wednesday (W)'])
  const [selectedSlots, setSelectedSlots] = useState<string[]>([])
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'warning'; message: string } | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const dayOptions = [
    'Monday (M)',
    'Tuesday (T)',
    'Wednesday (W)',
    'Thursday (R)',
    'Friday (F)',
  ]

  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([])

  useEffect(() => {
    let active = true
    timeSlotService.getTimeSlots().then((slots) => {
      if (active) setTimeSlots(slots)
    })
    instructorService.getInstructors().then((loaded) => {
      if (active) setInstructorList(loaded)
    })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (isLockedInstructor && user?.linked_user_id) {
      setSelectedInstructor(String(user.linked_user_id))
    }
  }, [isLockedInstructor, user?.linked_user_id])

  const instructors = React.useMemo(() => {
    const base = toInstructorOptions(instructorList)
    if (
      isLockedInstructor &&
      user?.linked_user_id &&
      !base.some((opt) => opt.value === String(user.linked_user_id))
    ) {
      base.unshift({
        value: String(user.linked_user_id),
        label: `${user.full_name} (${user.department})`,
      })
    }
    return base
  }, [instructorList, isLockedInstructor, user])

  const toggleDay = (day: string) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const toggleSlot = (slot: string) => {
    setSelectedSlots((prev) =>
      prev.includes(slot) ? prev.filter((s) => s !== slot) : [...prev, slot]
    )
  }

  const handleSavePreferences = async () => {
    if (selectedDays.length === 0 || selectedSlots.length === 0) {
      setToast({
        type: 'error',
        message: 'Please select at least one teaching day and one time slot.',
      })
      return
    }

    try {
      setIsSubmitting(true)
      const mappedDays = selectedDays.map((d) => {
        const match = d.match(/\((.*?)\)/)
        return match ? match[1] : d
      })

      await preferenceService.submitPreference({
        user_id: Number(selectedInstructor),
        semester_id: 1,
        preferred_days: mappedDays,
        preferred_slots: selectedSlots,
        preferred_rooms: [],
      })
      setToast({
        type: 'success',
        message: 'Instructor preferences saved successfully!',
      })
    } catch {
      setToast({
        type: 'error',
        message: 'Failed to save preferences. Please check backend connection.',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setSelectedDays([])
    setSelectedSlots([])
    setToast(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Instructor Preferences</h1>
        <p className="text-sm text-slate-500 mt-1">
          Specify teaching day patterns, time slot availability, and classroom layout needs.
        </p>
      </div>

      <Alert variant="info" title="Interactive Preferences Submission">
        Select an instructor, click to toggle preferred teaching days and time slots, and submit to save
        directly via{' '}
        <code className="bg-blue-100 px-1 py-0.5 rounded font-mono">POST /api/v1/preferences</code>.
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
              disabled={isLockedInstructor}
              helperText={
                isLockedInstructor
                  ? 'Locked to your authenticated faculty profile.'
                  : undefined
              }
              onChange={(e) => setSelectedInstructor(e.target.value)}
              data-testid="instructor-select"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Preferred Days <span className="text-red-500">*</span>
            </label>
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
                    data-testid={`day-btn-${day}`}
                  >
                    {day}
                  </Button>
                )
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Preferred Time Slots <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              {timeSlots.map((timeSlot) => {
                const slot = toSlotKey(timeSlot)
                const isSelected = selectedSlots.includes(slot)
                return (
                  <button
                    key={slot}
                    type="button"
                    data-testid={`slot-${slot}`}
                    onClick={() => toggleSlot(slot)}
                    className={`p-2.5 rounded-xl border text-xs flex items-center space-x-2 transition-all cursor-pointer text-left focus:outline-none ${
                      isSelected
                        ? 'bg-blue-50 border-blue-600 text-blue-700 font-semibold ring-2 ring-blue-500/20'
                        : 'border-slate-200 text-slate-600 bg-slate-50 hover:bg-slate-100/80 hover:border-slate-300'
                    }`}
                  >
                    <Clock
                      className={`w-3.5 h-3.5 flex-shrink-0 ${
                        isSelected ? 'text-blue-600' : 'text-slate-400'
                      }`}
                    />
                    <span className="truncate">{`${timeSlot.start_time} - ${timeSlot.end_time}`}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="pt-2 flex items-center space-x-3">
            <Button
              variant="primary"
              onClick={handleSavePreferences}
              isLoading={isSubmitting}
              leftIcon={<Check className="w-4 h-4" />}
              data-testid="save-preferences-button"
            >
              Save Preferences
            </Button>
            <Button
              variant="secondary"
              type="button"
              onClick={handleReset}
              disabled={isSubmitting}
              data-testid="reset-preferences-button"
            >
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}

export default PreferencesPage
