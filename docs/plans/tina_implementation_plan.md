# Sprint 1 Individual Implementation Plan: Tina Nguyen

**Name:** Tina Nguyen  
**Role:** Frontend Lead Engineer (UI Components, Preference Portal, Admin CRUD Management)  
**Assigned User Stories:** US-6, US-7  
**Assigned Acceptance Criteria:** AC 6.1, AC 6.2, AC 6.3, AC 7.1, AC 7.2, AC 7.3  
**Target LOC:** 700+ Lines of Code (Production + Automated Tests)  
**Branch:** `feature/tina-preference-admin-ui`  

---

## 1. Domain Ownership & Responsibilities

In Sprint 0, Tina initialized the React + Vite + Tailwind shell, configured the routing layout, and set up Vitest.  
In **Sprint 1**, Tina's primary objective is to replace static placeholders with **fully functional, interactive UI portals for Instructor Preferences and Resource Administration**:
1. Transform `PreferencesPage.tsx` into a **reactive preference submission portal** with instructor selection, day pattern toggles (MWF, TR), time-slot availability grids, and client-side form validation.
2. Build an **Admin Resource Management Portal** (`CourseManager.tsx` and `RoomManager.tsx`) featuring real-time search, department filtering, modal dialogs for adding courses/rooms, and delete actions.
3. Build a reusable **Toast Notification System** (`Toast.tsx`) providing instant visual feedback for success and error states.
4. Author comprehensive Vitest component tests testing form validation, user interactions, and modal lifecycles.

---

## 2. Step-by-Step Task Checklist

```
[ ] Step 1: Create Git Branch 'feature/tina-preference-admin-ui'
[ ] Step 2: Implement Reusable Toast Notification ('frontend/src/components/common/Toast.tsx')
[ ] Step 3: Implement Dynamic Preferences Page ('frontend/src/pages/PreferencesPage.tsx')
[ ] Step 4: Implement Course Management Portal ('frontend/src/components/admin/CourseManager.tsx')
[ ] Step 5: Implement Room Management Portal ('frontend/src/components/admin/RoomManager.tsx')
[ ] Step 6: Integrate Tabs in Admin Portal ('frontend/src/pages/AdminPage.tsx')
[ ] Step 7: Author Automated Component Tests in Vitest
[ ] Step 8: Verify 100% Test Pass Rate via 'npm test'
[ ] Step 9: Rehearse Segment 3 for the 5-Minute Demonstration Video
```

---

## 3. Detailed Technical Implementation

### Task 1: Reusable Toast Notification System (`frontend/src/components/common/Toast.tsx`)
* **File Location:** `frontend/src/components/common/Toast.tsx` (~70 LOC)
* **Purpose:** Provide pop-up alert notifications for operations like "Course added successfully", "Preferences submitted", or "Invalid form inputs".
* **Key Features:**
  * Supports variants: `'success'`, `'error'`, `'warning'`, `'info'`.
  * Auto-dismiss after 4 seconds with smooth slide-in transition.
  * Close button and icon indicators.

### Task 2: Reactive Preference Submission Portal (`frontend/src/pages/PreferencesPage.tsx`)
* **File Location:** `frontend/src/pages/PreferencesPage.tsx` (~180 LOC)
* **State & Features:**
  * `selectedInstructorId`: Number (loaded from `/api/v1/courses` or mock users).
  * `selectedDays`: `string[]` (e.g., `['Monday', 'Wednesday']`). Toggling buttons updates state with active blue styles. (Satisfies **AC 6.1**).
  * `selectedSlots`: `string[]` (e.g., `['09:00 - 09:50']`).
  * `preferredRoomType`: `'lecture' | 'lab'`.
  * **Validation & Submit Handler:**
    * If `selectedDays.length === 0` or `selectedSlots.length === 0`, triggers warning toast: `"Please select at least one teaching day and time slot."` (Satisfies **AC 6.3**).
    * On valid submit, calls `apiClient.post('/preferences', ...)` and triggers success toast: `"Preferences submitted successfully!"` (Satisfies **AC 6.2**).

### Task 3: Course Management Portal (`frontend/src/components/admin/CourseManager.tsx`)
* **File Location:** `frontend/src/components/admin/CourseManager.tsx` (~180 LOC)
* **Features:**
  * Real-time search input filtering courses by code or title (Satisfies **AC 7.1**).
  * Department dropdown filter (`CS`, `ECE`, `MATH`, `All`).
  * **Add Course Modal:** Form with Course Code, Course Name, Department, Credits, Enrollment, and Lab Checkbox. Validates positive enrollment and required fields before sending `POST /api/v1/courses` (Satisfies **AC 7.2**).
  * **Delete Action:** Trash icon triggers confirmation modal, calls `DELETE /api/v1/courses/{id}`, and removes item from local list (Satisfies **AC 7.3**).

### Task 4: Room Management Portal (`frontend/src/components/admin/RoomManager.tsx`)
* **File Location:** `frontend/src/components/admin/RoomManager.tsx` (~140 LOC)
* **Features:**
  * Tabular display of rooms: Room Number, Building, Capacity, Type (`Lecture` vs `Lab`).
  * Filter pills for Room Type (`All`, `Lecture`, `Lab`).
  * Add Room modal calling `POST /api/v1/rooms`.

### Task 5: Admin Page Integration (`frontend/src/pages/AdminPage.tsx`)
* **File Location:** `frontend/src/pages/AdminPage.tsx` (~110 LOC)
* **Features:**
  * Tab navigation bar: `[Course Management]`, `[Classroom Management]`, `[Solver Diagnostics]`.
  * Renders `CourseManager` or `RoomManager` seamlessly inside the admin layout.

### Task 6: Automated Vitest Test Suite
* **Files to Create:**
  * `frontend/src/pages/__tests__/PreferencesPage.test.tsx` (~140 LOC)
    * `renders preference form with day selection buttons`
    * `toggles day button state on user click`
    * `shows validation warning when submitting with empty fields`
    * `submits form and displays success toast when inputs are valid`
  * `frontend/src/components/admin/__tests__/CourseManager.test.tsx` (~130 LOC)
    * `renders list of courses in table`
    * `filters table rows when search query is typed`
    * `opens Add Course modal on button click`
    * `validates required fields before submitting new course`
  * `frontend/src/components/admin/__tests__/RoomManager.test.tsx` (~90 LOC)
    * `filters rooms by lab type`
    * `renders capacity badges with proper color coding`

---

## 4. LOC Contribution Breakdown for Tina

| File | Type | Purpose | LOC Estimate |
| :--- | :--- | :--- | :---: |
| `frontend/src/components/common/Toast.tsx` | Production | Pop-up notification alert system | ~70 |
| `frontend/src/pages/PreferencesPage.tsx` | Production | Reactive preference submission portal | ~180 |
| `frontend/src/components/admin/CourseManager.tsx` | Production | Searchable course catalog admin table & modals | ~180 |
| `frontend/src/components/admin/RoomManager.tsx` | Production | Classroom/lab admin manager table | ~140 |
| `frontend/src/pages/AdminPage.tsx` | Production | Admin tabbed shell and solver diagnostics | ~110 |
| `frontend/src/pages/__tests__/PreferencesPage.test.tsx` | Test | Form interaction and validation tests | ~140 |
| `frontend/src/components/admin/__tests__/CourseManager.test.tsx` | Test | Course manager table and modal tests | ~130 |
| `frontend/src/components/admin/__tests__/RoomManager.test.tsx` | Test | Room filter and render tests | ~90 |
| **Total LOC Expected** | | | **~1,040 LOC** (Compliant: > 400 LOC) |

---

## 5. Verification Commands

Run the following commands to verify implementation correctness:
```bash
# 1. Run Vitest component test suites
npm test -- --run

# 2. Run test coverage
npm test -- --coverage

# 3. Start development server to inspect UI
npm run dev
# Open browser at: http://localhost:5173
```

---

## 6. Video Demonstration Coordination
Tina will present **Segment 3** (1:45 - 2:45) showcasing the live user interface: navigating to the Admin page, searching for courses, adding a course via modal, navigating to the Preferences page, selecting teaching days, and submitting the form with live toast feedback.
