# Sprint 1 Individual Implementation Plan: Tina Nguyen

**Name:** Tina Nguyen  
**Role:** Frontend Engineer (Interactive Preferences Portal, Schedule Multi-Filters & Export, Toast Notification System)  
**Assigned User Stories:** US-6 (Instructor Preference Portal), US-8 (Schedule Multi-Filters), US-9 (Schedule Export)  
**Assigned Acceptance Criteria:** AC 6.1, AC 6.2, AC 6.3, AC 8.1, AC 8.2, AC 9.2  
**Target LOC:** 680+ Lines of Code (Production + Automated Vitest Tests)  
**Branch:** `feature/tina-preference-schedule-ui`  

---

## 1. Domain Ownership & Responsibilities

In Sprint 0, Tina initialized the React + Vite + Tailwind shell, configured the routing layout, and set up Vitest.  
In **Sprint 1**, following Sal's delivery of the foundational UI component library and API services (`origin/client_api`), Tina's primary objective is to **deliver the interactive frontend features required for the live demonstration (Segments 3 and 4)**:
1. **Interactive Instructor Preferences Portal (`PreferencesPage.tsx`)**:
   - Replace static time-slot cards with a dynamic, multi-selectable availability grid connected to `GET /api/v1/time-slots`.
   - Wire the `"Save Preferences"` button to `preferenceService.submitPreference()` (`POST /api/v1/preferences`).
   - Implement client-side form validation (requiring at least one day and one time slot).
2. **Reusable Toast Notification System (`Toast.tsx`)**:
   - Build a non-intrusive floating toast notification component with auto-dismiss (4 seconds) and status styles (success green, error red, warning amber).
3. **Schedule Multi-Dimension Filter Toolbar (`ScheduleFilters.tsx`) on `SchedulePage.tsx`**:
   - Enable real-time timetable filtering by **Department (CS, ECE, MATH, All)**, **Instructor**, and **Room** directly on FullCalendar without reloading the page.
4. **Schedule Export Utility (`exportSchedule.ts`)**:
   - Implement a one-click **"Export CSV"** button on `SchedulePage` that generates and downloads a structured `.csv` file containing the active semester's timetable.
5. **Automated Vitest Test Suites**:
   - Author thorough unit tests for the Preferences form and Schedule filter toolbar to satisfy the **400+ LOC** individual Git contribution requirement.

---

## 2. Step-by-Step Task Checklist

```
[ ] Step 1: Create Git Branch 'feature/tina-preference-schedule-ui' from latest 'main'
[ ] Step 2: Implement Reusable Toast Component ('frontend/src/components/common/Toast.tsx')
[ ] Step 3: Implement Interactive Time-Slot Picker & API Submission in 'frontend/src/pages/PreferencesPage.tsx'
[ ] Step 4: Implement Schedule Export Utility ('frontend/src/utils/exportSchedule.ts')
[ ] Step 5: Implement Multi-Dimension Filter Component ('frontend/src/components/schedule/ScheduleFilters.tsx')
[ ] Step 6: Integrate ScheduleFilters and Export Button into 'frontend/src/pages/SchedulePage.tsx'
[ ] Step 7: Author Vitest Automated Test Suites ('PreferencesPage.test.tsx' & 'ScheduleFilters.test.tsx')
[ ] Step 8: Verify 100% Test Pass Rate via 'npm test'
[ ] Step 9: Push branch to GitHub and open Pull Request into 'main'
[ ] Step 10: Rehearse Segment 3 (1:45 – 2:45) for the 5-Minute Demonstration Video
```

---

## 3. Detailed Technical Implementation

### Task 1: Reusable Toast Notification System (`frontend/src/components/common/Toast.tsx`)
* **File Location:** `frontend/src/components/common/Toast.tsx` (~80 LOC)
* **Purpose:** Display floating notifications on form submissions or API errors.
* **Component Specification:**
  ```typescript
  import React, { useEffect } from 'react'
  import { CheckCircle, AlertCircle, X } from 'lucide-react'

  export interface ToastProps {
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
    onClose: () => void
    duration?: number
  }

  export const Toast: React.FC<ToastProps> = ({ type, message, onClose, duration = 4000 }) => {
    useEffect(() => {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }, [onClose, duration])

    const styles = {
      success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
      error: 'bg-red-50 border-red-200 text-red-800',
      warning: 'bg-amber-50 border-amber-200 text-amber-800',
      info: 'bg-blue-50 border-blue-200 text-blue-800',
    }

    return (
      <div className={`fixed bottom-5 right-5 z-50 flex items-center space-x-3 p-4 rounded-xl border shadow-lg ${styles[type]}`}>
        {type === 'success' ? <CheckCircle className="w-5 h-5 text-emerald-600" /> : <AlertCircle className="w-5 h-5 text-red-600" />}
        <span className="text-sm font-medium">{message}</span>
        <button onClick={onClose} className="p-1 hover:opacity-75">
          <X className="w-4 h-4" />
        </button>
      </div>
    )
  }
  ```

---

### Task 2: Interactive Preference Submission Portal (`frontend/src/pages/PreferencesPage.tsx`)
* **File Location:** `frontend/src/pages/PreferencesPage.tsx` (~170 LOC)
* **Key Enhancements:**
  1. **Dynamic State Management:**
     ```typescript
     const [selectedInstructor, setSelectedInstructor] = useState('1')
     const [selectedDays, setSelectedDays] = useState<string[]>(['MWF'])
     const [selectedSlots, setSelectedSlots] = useState<string[]>([])
     const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
     const [isSubmitting, setIsSubmitting] = useState(false)
     ```
  2. **Interactive Time-Slot Selection:**
     - Replace static gray blocks with clickable toggle buttons.
     - Active slots highlight with `bg-blue-50 border-blue-600 text-blue-700 font-semibold ring-2 ring-blue-500/20`.
     - Clicking toggles inclusion in `selectedSlots` array (Satisfies **AC 6.1**).
  3. **Backend API Integration (`preferenceService.submitPreference`):**
     ```typescript
     const handleSavePreferences = async () => {
       if (selectedDays.length === 0 || selectedSlots.length === 0) {
         setToast({ type: 'error', message: 'Please select at least one teaching day and one time slot.' })
         return
       }
       try {
         setIsSubmitting(true)
         await preferenceService.submitPreference({
           user_id: Number(selectedInstructor),
           semester_id: 1,
           preferred_days: selectedDays,
           preferred_slots: selectedSlots,
           preferred_rooms: [],
         })
         setToast({ type: 'success', message: 'Instructor preferences saved successfully!' })
       } catch (err) {
         setToast({ type: 'error', message: 'Failed to save preferences. Please check backend connection.' })
       } finally {
         setIsSubmitting(false)
       }
     }
     ```
  - Displays `Toast` component upon completion (Satisfies **AC 6.2** & **AC 6.3**).

---

### Task 3: Multi-Dimension Schedule Filters (`frontend/src/components/schedule/ScheduleFilters.tsx`)
* **File Location:** `frontend/src/components/schedule/ScheduleFilters.tsx` (~110 LOC)
* **Key Features:**
  - Department dropdown filter: `All Departments`, `CS (Computer Science)`, `ECE (Electrical & Computer Eng)`, `MATH (Mathematics)`.
  - Search input for live keyword filtering across course codes, instructor names, or room numbers.
  - Reset button to clear active filters.
  - Calls `onFilterChange({ department, search })` callback to dynamically filter calendar events without page reloads (Satisfies **AC 8.1** & **AC 8.2**).

---

### Task 4: Schedule Export Utility (`frontend/src/utils/exportSchedule.ts`)
* **File Location:** `frontend/src/utils/exportSchedule.ts` (~80 LOC)
* **Key Functions to Write:**
  ```typescript
  import { ScheduleEvent } from '../types/api'

  export function exportScheduleToCSV(events: ScheduleEvent[], semesterName: string): void {
    const headers = ['Course Code', 'Course Name', 'Instructor', 'Room', 'Day Pattern', 'Start Time', 'End Time', 'Status']
    const rows = events.map(e => [
      e.course_code,
      `"${e.course_name}"`,
      `"${e.instructor_name}"`,
      e.room_number,
      e.day_pattern,
      e.start_time,
      e.end_time,
      e.status
    ])

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `UMKC_Schedule_${semesterName.replace(/\s+/g, '_')}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
  ```
* **Acceptance Mapping:** Satisfies **AC 9.2** (one-click CSV timetable download).

---

### Task 5: Schedule Page Integration (`frontend/src/pages/SchedulePage.tsx`)
* **File Location:** `frontend/src/pages/SchedulePage.tsx` (~60 LOC addition)
* **Integration Steps:**
  - Mount `<ScheduleFilters onFilterChange={handleFilterChange} />` below the semester selector.
  - Add an `"Export CSV"` button in the header triggering `exportScheduleToCSV(activeEvents, currentSemesterName)`.

---

### Task 6: Automated Vitest Test Suite
* **Files to Create:**
  1. `frontend/src/pages/__tests__/PreferencesPage.test.tsx` (~120 LOC)
     - `renders preference form with instructor selector`
     - `toggles day selection buttons`
     - `toggles time slot selection buttons`
     - `displays error toast when submitted without day or time slot`
     - `submits preference to API and displays success toast`
  2. `frontend/src/components/schedule/__tests__/ScheduleFilters.test.tsx` (~80 LOC)
     - `renders department selector and search input`
     - `calls onFilterChange when department is selected`
     - `resets filters on Reset button click`

---

## 4. LOC Contribution Breakdown for Tina

| File | Type | Purpose | LOC Estimate |
| :--- | :--- | :--- | :---: |
| `frontend/src/components/common/Toast.tsx` | Production | Floating notification alert component | ~80 |
| `frontend/src/pages/PreferencesPage.tsx` | Production | Interactive preference portal & API submit | ~170 |
| `frontend/src/components/schedule/ScheduleFilters.tsx` | Production | Multi-dimension schedule filter toolbar | ~110 |
| `frontend/src/utils/exportSchedule.ts` | Production | Schedule CSV export and download generator | ~80 |
| `frontend/src/pages/SchedulePage.tsx` | Production | Filter toolbar and Export button integration | ~60 |
| `frontend/src/pages/__tests__/PreferencesPage.test.tsx` | Test | Preference form interaction and validation tests | ~120 |
| `frontend/src/components/schedule/__tests__/ScheduleFilters.test.tsx` | Test | Schedule filter toolbar unit tests | ~80 |
| **Total LOC Expected** | | | **~700 LOC** (Compliant: > 400 LOC) |

---

## 5. Verification Commands

Run the following commands in `frontend/` to verify implementation:
```bash
# 1. Run Vitest component test suites
npm test

# 2. Run dev server to inspect UI interactively
npm run dev
# Open browser at: http://localhost:5173/preferences and http://localhost:5173/schedule
```

---

## 6. Video Demonstration Coordination
Tina will present **Segment 3** (1:45 – 2:45) in the 5-Minute Demonstration Video:
1. Navigate to `http://localhost:5173/preferences`.
2. Select an instructor (Dr. Yugyung Lee).
3. Toggle teaching days (`MWF`) and click two time slots (`09:30 - 10:45` and `11:00 - 12:15`).
4. Click `"Save Preferences"` and show the live green toast notification.
5. Inspect the Network tab to show the successful `POST /api/v1/preferences` response.
