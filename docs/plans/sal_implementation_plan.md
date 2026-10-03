# Sprint 1 Individual Implementation Plan: Salvatore Nigro

**Name:** Salvatore Nigro  
**Role:** Frontend Lead Engineer (FullCalendar Matrix, Multi-Filters, Solver Dashboard, Export)  
**Assigned User Stories:** US-8, US-9  
**Assigned Acceptance Criteria:** AC 8.1, AC 8.2, AC 8.3, AC 9.1, AC 9.2  
**Target LOC:** 690+ Lines of Code (Production + Automated Tests)  
**Branch:** `feature/sal-calendar-matrix-export`  

---

## 1. Domain Ownership & Responsibilities

In Sprint 0, Sal integrated the FullCalendar library skeleton, authored the mock dataset schema, and built the API client layer.  
In **Sprint 1**, Sal's primary objective is to turn the timetable calendar into a **fully dynamic, interactive matrix connected to live backend data**:
1. Connect FullCalendar directly to live schedule events retrieved from `GET /api/v1/schedules?semester_id=X`.
2. Build an advanced **Schedule Filter Toolbar** (`ScheduleFilters.tsx`) enabling instant filtering by Department, Instructor, and Classroom without page reloads.
3. Implement an **Interactive Event Popover Modal** displaying granular course info (enrolled students, room capacity, instructor email, credits).
4. Build the **Solver Control Panel** (`SolverControlPanel.tsx`) that triggers `POST /api/v1/solver/run` from the UI with real-time spinner feedback and metrics.
5. Implement the **Schedule Export Utility** (`exportSchedule.ts`) supporting one-click CSV and JSON downloads.
6. Author comprehensive Vitest test suites for calendar rendering, filter logic, and export generators.

---

## 2. Step-by-Step Task Checklist

```
[ ] Step 1: Create Git Branch 'feature/sal-calendar-matrix-export'
[ ] Step 2: Implement Schedule Export Utility ('frontend/src/utils/exportSchedule.ts')
[ ] Step 3: Implement Multi-Dimension Filter Component ('frontend/src/components/schedule/ScheduleFilters.tsx')
[ ] Step 4: Implement Solver Control Panel ('frontend/src/components/schedule/SolverControlPanel.tsx')
[ ] Step 5: Enhance Schedule Calendar with Event Popover ('frontend/src/components/schedule/ScheduleCalendar.tsx')
[ ] Step 6: Expand Schedule Service API Client ('frontend/src/services/scheduleService.ts')
[ ] Step 7: Update Schedule Page View ('frontend/src/pages/SchedulePage.tsx')
[ ] Step 8: Author Vitest Automated Tests for Calendar, Filters, and Export
[ ] Step 9: Verify 100% Test Pass Rate via 'npm test'
[ ] Step 10: Rehearse Segment 4 for the 5-Minute Demonstration Video
```

---

## 3. Detailed Technical Implementation

### Task 1: Schedule Export Utility (`frontend/src/utils/exportSchedule.ts`)
* **File Location:** `frontend/src/utils/exportSchedule.ts` (~90 LOC)
* **Key Functions to Write:**
  ```typescript
  export function exportScheduleToCSV(events: ScheduleEvent[], semesterName: string): void {
    // Converts schedule events into structured CSV headers and rows:
    // "Course Code,Course Name,Department,Instructor,Room,Day,Start Time,End Time"
    // Creates a Blob and triggers automatic browser download
  }

  export function exportScheduleToJSON(events: ScheduleEvent[], semesterName: string): void {
    // Downloads beautified JSON payload of current semester timetable
  }
  ```
* **Acceptance Mapping:** Satisfies **AC 9.2** (one-click CSV and JSON timetable download).

### Task 2: Multi-Dimension Filter Toolbar (`frontend/src/components/schedule/ScheduleFilters.tsx`)
* **File Location:** `frontend/src/components/schedule/ScheduleFilters.tsx` (~130 LOC)
* **Filters Implemented:**
  * **Department:** Dropdown (`All Departments`, `CS`, `ECE`, `MATH`, `BIOL`, etc.)
  * **Instructor Search:** Real-time text search for faculty name.
  * **Room Type / Building:** Dropdown to isolate laboratory spaces or specific halls.
* **Acceptance Mapping:** Satisfies **AC 8.2** (instant client-side filtering without page reloads).

### Task 3: Solver Control Panel Component (`frontend/src/components/schedule/SolverControlPanel.tsx`)
* **File Location:** `frontend/src/components/schedule/SolverControlPanel.tsx` (~120 LOC)
* **Features:**
  * **"Generate Optimal Schedule" Button:** Triggers `scheduleService.triggerSolver(semesterId)`.
  * **Loading State:** Button shows rotating spinner and text `"Optimizing with CP-SAT..."` while request is in flight.
  * **Metrics Badge:** On success, displays solve status (`OPTIMAL`), solve runtime (`2.4s`), and total scheduled courses (`40`).
* **Acceptance Mapping:** Satisfies **AC 9.1** (on-demand solver trigger from the browser).

### Task 4: FullCalendar Enhancements & Event Popover (`frontend/src/components/schedule/ScheduleCalendar.tsx`)
* **File Location:** `frontend/src/components/schedule/ScheduleCalendar.tsx` (~170 LOC)
* **Features:**
  * **Color-coding by Department:** CS courses in royal blue, ECE in emerald green, MATH in indigo, Biology in purple.
  * **Click Handler:** Clicking any calendar course opens an event detail modal showing:
    * Course code & full course title
    * Instructor name & email
    * Classroom number, building, and capacity vs enrollment
    * Meeting pattern (e.g., MWF 09:00 - 09:50)
* **Acceptance Mapping:** Satisfies **AC 8.1** (full week grid) and **AC 8.3** (event click popover).

### Task 5: Schedule Service Client Updates (`frontend/src/services/scheduleService.ts`)
* **File Location:** `frontend/src/services/scheduleService.ts` (~80 LOC)
* **Methods:**
  * `getSchedules(semesterId: number)`: Calls `GET /api/v1/schedules?semester_id=${semesterId}`.
  * `triggerSolver(semesterId: number)`: Calls `POST /api/v1/solver/run`.
  * `exportSchedule(semesterId: number, format: 'csv' | 'json')`: Invokes export utility.

### Task 6: Automated Vitest Test Suite
* **Files to Create:**
  * `frontend/src/components/schedule/__tests__/ScheduleCalendar.test.tsx` (~130 LOC)
    * `renders FullCalendar with 5 weekday columns`
    * `displays loading indicator while schedule loads`
    * `opens course detail popover when course event is clicked`
  * `frontend/src/components/schedule/__tests__/ScheduleFilters.test.tsx` (~110 LOC)
    * `filters displayed events when department filter changes`
    * `resets filters when Clear button is clicked`
  * `frontend/src/utils/__tests__/exportSchedule.test.ts` (~90 LOC)
    * `generates valid CSV string with correct header columns`
    * `handles empty event list gracefully without throwing errors`

---

## 4. LOC Contribution Breakdown for Sal

| File | Type | Purpose | LOC Estimate |
| :--- | :--- | :--- | :---: |
| `frontend/src/utils/exportSchedule.ts` | Production | CSV and JSON file export utility | ~90 |
| `frontend/src/components/schedule/ScheduleFilters.tsx` | Production | Multi-filter toolbar (Department, Instructor, Room) | ~130 |
| `frontend/src/components/schedule/SolverControlPanel.tsx` | Production | On-demand solver run button and status badge | ~120 |
| `frontend/src/components/schedule/ScheduleCalendar.tsx` | Production | FullCalendar matrix with popovers & colors | ~170 |
| `frontend/src/services/scheduleService.ts` | Production | Schedule API and solver trigger service client | ~80 |
| `frontend/src/components/schedule/__tests__/ScheduleCalendar.test.tsx` | Test | Calendar rendering and interaction tests | ~130 |
| `frontend/src/components/schedule/__tests__/ScheduleFilters.test.tsx` | Test | Filter logic unit tests | ~110 |
| `frontend/src/utils/__tests__/exportSchedule.test.ts` | Test | Export formatting and blob generator tests | ~90 |
| **Total LOC Expected** | | | **~920 LOC** (Compliant: > 400 LOC) |

---

## 5. Verification Commands

Run the following commands to verify implementation correctness:
```bash
# 1. Run Vitest test suites
npm test -- --run

# 2. Run schedule-specific tests only
npx vitest run src/components/schedule/ src/utils/__tests__/

# 3. Start local UI server
npm run dev
```

---

## 6. Video Demonstration Coordination
Sal will present **Segment 4** (2:45 - 4:00) demonstrating the live interactive schedule matrix: navigating through the weekly calendar, applying department filters, clicking a course card to inspect details, triggering the on-demand CP-SAT solver, and demonstrating the CSV export download.
