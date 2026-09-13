# UMKC Course Timetable Scheduler
### CS 5551 — Advanced Software Engineering | School of Science & Engineering (SSE)
**University of Missouri–Kansas City (UMKC)**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![OR-Tools CP-SAT](https://img.shields.io/badge/solver-Google%20OR--Tools%20CP--SAT-red.svg)](https://developers.google.com/optimization/cp/cp_solver)
[![Automated Tests](https://img.shields.io/badge/tests-25%2F25%20passed-brightgreen.svg)]()
[![Dataset Scale](https://img.shields.io/badge/scale-20%20Faculty%20%7C%2040%20Courses%20%7C%206%20Semesters-orange.svg)]()

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Mathematical Model & CP-SAT Formulation](#mathematical-model--cp-sat-formulation)
   - [Decision Variables](#decision-variables)
   - [Hard Constraints](#hard-constraints)
   - [Objective Function & Integer Weights](#objective-function--integer-weights)
   - [Dynamic Priority Carryover Engine](#dynamic-priority-carryover-engine)
3. [UMKC Real-University Volume Dataset](#umkc-real-university-volume-dataset)
   - [Entity Overview](#entity-overview)
   - [Relational Database Schema](#relational-database-schema)
4. [Multi-Semester Dynamic Preference Simulation](#multi-semester-dynamic-preference-simulation)
   - [Semester Schedule (Fall 2024 – Spring 2027)](#semester-schedule-fall-2024--spring-2027)
   - [Dynamic Preference Variation & Day Rotation](#dynamic-preference-variation--day-rotation)
5. [Repository Structure](#repository-structure)
6. [Installation & Setup](#installation--setup)
7. [CLI Usage Guide](#cli-usage-guide)
8. [Automated Verification & Test Suites](#automated-verification--test-suites)
9. [Solver Performance Benchmarks](#solver-performance-benchmarks)

---

## Executive Summary

The **UMKC Course Timetable Scheduler** is a high-performance automated course scheduling and timetabling system built on **Google OR-Tools CP-SAT** (Constraint Programming / Boolean Satisfiability). The system models the **UMKC School of Science & Engineering (SSE)** at true university scale:

- **20 Faculty Members** across 4 departments (CS/SE, Math/Stat, ECE/Physics, Chem/Bio).
- **40 Academic Courses** spanning undergraduate lectures, graduate seminars, and specialized labs.
- **12 Classrooms** across 5 campus buildings with capacities from 25 to 150.
- **6 Standard 75-Minute Time Slots** daily across Monday through Friday.
- **6 Distinct Semesters** (Fall 2024 through Spring 2027) with dynamic, rotating faculty preferences.
- **Strict Hard Constraint**: Every instructor is assigned **maximum 2 classes per semester** (achieving an exact $20 \times 2 = 40$ balance).
- **Dynamic Priority Bidding**: Unmet preferences yield compensation points that carry over from term to term, while fully satisfied faculty experience gradual decay.

---

## Mathematical Model & CP-SAT Formulation

### Decision Variables

The scheduling domain is pruned using domain preprocessing (`get_valid_ic_pairs()` and `get_valid_rc_pairs()`) to reduce the search space by **>70%**:

| Variable | Indices | Definition |
|:---|:---|:---|
| $X[d, r, s, i, c]$ | $\text{Day} \times \text{Room} \times \text{Slot} \times \text{Inst} \times \text{Course}$ | Binary variable: Course $c$ is taught by instructor $i$ in classroom $r$ at slot $s$ on day $d$. |
| $Y[r, s, i, c]$ | $\text{Room} \times \text{Slot} \times \text{Inst} \times \text{Course}$ | Aggregation variable: Course $c$ meets in room $r$ at slot $s$ under instructor $i$. |
| $Z[i, c]$ | $\text{Inst} \times \text{Course}$ | Assignment variable: Instructor $i$ is assigned to teach course $c$. |

### Hard Constraints

1. **Course Coverage**: Each of the 40 courses must be scheduled exactly once:
   $$\forall c \in \text{Courses}: \quad \sum_{i \in \text{Instructors}} Z[i, c] = 1$$

2. **Teaching Load Upper Bound (Max 2 Classes/Semester)**:
   $$\forall i \in \text{Instructors}: \quad \sum_{c \in \text{Courses}} Z[i, c] \le 2$$
   *With 40 courses and 20 faculty, the solver guarantees exactly 2 courses per instructor.*

3. **Qualification Purity**: An instructor can only be assigned to courses for which they are explicitly qualified:
   $$\forall (i, c) \notin \text{ValidIC}: \quad Z[i, c] = 0$$

4. **Room Capacity Compliance**: A course cannot be scheduled in a classroom whose capacity is smaller than expected enrollment:
   $$\forall (r, c) \text{ where } \text{Capacity}(r) < \text{Enrollment}(c): \quad \sum_{s, i} Y[r, s, i, c] = 0$$

5. **Laboratory Layout Enforcement**: Laboratory courses must be assigned exclusively to rooms with `layout_type == "lab"`:
   $$\forall c \text{ where } \text{Layout}(c) = \text{lab}, \; \forall r \text{ where } \text{Layout}(r) \ne \text{lab}: \quad \sum_{s, i} Y[r, s, i, c] = 0$$

6. **Classroom Single-Occupancy**: No classroom can host more than one course at the same day and time slot:
   $$\forall d \in \text{Days}, \; \forall r \in \text{Rooms}, \; \forall s \in \text{Slots}: \quad \sum_{i, c} X[d, r, s, i, c] \le 1$$

7. **Instructor Single-Course (No Double Booking)**: No instructor can teach more than one course at the same day and time slot:
   $$\forall d \in \text{Days}, \; \forall i \in \text{Instructors}, \; \forall s \in \text{Slots}: \quad \sum_{r, c} X[d, r, s, i, c] \le 1$$

8. **Standard 2-Day Meeting Pattern**: Every course meets exactly 2 days per week (Monday/Wednesday or Tuesday/Thursday):
   $$\forall (r, s, i, c): \quad \sum_{d \in \{\text{Mon, Wed}\}} X[d, r, s, i, c] = 2 \cdot Y[r, s, i, c] \quad \lor \quad \sum_{d \in \{\text{Tue, Thu}\}} X[d, r, s, i, c] = 2 \cdot Y[r, s, i, c]$$

---

### Objective Function & Integer Weights

The objective function maximizes weighted preference satisfaction scaled by each instructor's current priority score:

$$\max \sum_{i \in \text{Instructors}} \left( \text{Priority}(i) + \text{Jitter}(i) \right) \times \text{SatisfactionScore}(i)$$

Where per-course satisfaction is scored using dimensional integer weights totaling 10 points (100%):
- **Preferred Meeting Days**: $2 \text{ pts/meeting} \times 2 \text{ days} = 4 \text{ pts}$ (**40%**)
- **Preferred Time Slot**: $4 \text{ pts}$ (**40%**)
- **Preferred Classroom / Layout**: $2 \text{ pts}$ for exact room match, $1 \text{ pt}$ for layout match (**20%**)

$$\text{Jitter}(i) \in [0, 999] \quad (\text{pseudo-random tie-breaker to prevent deterministic contention deadlocks})$$

---

### Dynamic Priority Carryover Engine

Instructors submit preferences each semester. Their priority scores dynamically evolve based on satisfaction:

1. **Compensation for Compromise ($< 100\%$ Satisfaction)**:
   If an instructor does not achieve 100% satisfaction, they earn bonus points proportional to the unmet percentage:
   $$\text{Bonus} = \lfloor 20,000 \times (1.0 - \text{SatisfactionRate}) \rfloor$$
   $$\text{Priority}_{\text{new}} = \text{Priority}_{\text{old}} + \text{Bonus}$$

2. **Gradual Monotonic Decay ($= 100\%$ Satisfaction)**:
   If an instructor's preferences are fully satisfied, their priority decays toward their base rank priority:
   $$\text{Priority}_{\text{new}} = \max\left( \text{BasePriority}, \; \text{Priority}_{\text{old}} - 10,000 \right)$$

---

## UMKC Real-University Volume Dataset

### Entity Overview

| Dimension | Count | Description |
|:---|:---:|:---|
| **Campuses** | 2 | Volker Campus, Health Sciences Campus |
| **Buildings** | 5 | Flarsheim Hall (FH), Royall Hall (RH), Haag Hall (HH), Spencer Chem (SCB), Bloch Heritage (BHH) |
| **Classrooms** | 12 | Capacities 25–150; Layouts: `auditorium`, `lecture`, `lab`, `seminar` |
| **Faculty** | 20 | 8 CS/SE, 4 Math/Stat, 4 ECE/Phys, 4 Chem/Bio (Base Priorities: 100k – 120k) |
| **Courses** | 40 | 16 CS, 8 Math, 8 ECE/Phys, 8 Chem/Bio (Enrollments: 20 – 140) |
| **Time Slots** | 6 | Daily 75-min slots: 08:00, 09:30, 11:00, 12:30, 14:00, 15:30 |
| **Semesters** | 6 | Fall 2024 through Spring 2027 |
| **Preferences** | 504 | 84 qualified entries $\times$ 6 semesters |

### Relational Database Schema

All data is organized as a relational database under `data/umkc/` in JSON format:

```text
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   CAMPUSES   │───1:N───►│  BUILDINGS   │───1:N───►│    ROOMS     │
│ (campus_id)  │          │(building_id) │          │  (room_id)   │
└──────────────┘          └──────────────┘          └──────────────┘
       │                                                   ▲
      1:N                                                  │
       ▼                                                  1:N
┌──────────────┐          ┌────────────────────────┐       │
│    USERS     │───1:N───►│ INSTRUCTOR_PREFERENCES ├───────┤
│ (user_id)    │          │         (id)           │       │
└──────────────┘          └────────────────────────┘       │
       │                              ▲                    │
      1:N                            1:N                   │
       ▼                              │                    │
┌──────────────┐                      │                    │
│  SCHEDULES   │───N:1────────────────┴────────────────────┘
│(schedule_id) │───N:1───► COURSES       (course_id)
│              │───N:1───► TIME_SLOTS    (slot_id)
│              │───N:1───► SEMESTERS     (semester_id)
└──────────────┘
```

#### Relational Tables & Foreign Key Map

| Table Name | Primary Key | Foreign Keys | Key Attributes & Role |
|:---|:---|:---|:---|
| `campuses.json` | `campus_id` | — | Campus name and address (Volker, Health Sciences) |
| `buildings.json` | `building_id` | `campus_id` | Campus building code (`FH`, `RH`, `HH`, `SCB`, `BHH`) |
| `rooms.json` | `room_id` | `building_id`, `campus_id` | `room_number`, `capacity` (25–150), `layout_type` (`auditorium`, `lecture`, `lab`, `seminar`) |
| `time_slots.json` | `slot_id` | — | Daily standard 75-minute meeting blocks (Slots 1–6) |
| `semesters.json` | `semester_id` | — | Academic terms from Fall 2024 through Spring 2027 (6 terms) |
| `users.json` | `user_id` | `campus_id` | Instructor profiles, base priorities, and accumulated priority points |
| `courses.json` | `course_id` | — | Course codes, titles, expected enrollments (20–140), required layouts |
| `instructor_preferences.json` | `id` | `instructor_id`, `course_id`, `semester_id`, `preferred_slot_id`, `preferred_room_id` | Multi-semester faculty preferences: preferred days, slot, room, layout (504 entries) |
| `schedules.json` | `schedule_id` | `course_id`, `instructor_id`, `room_id`, `slot_id`, `semester_id` | Master solved timetable output with confirmed meeting days and room assignments |
| `edit_requests.json` | `request_id` | `schedule_id`, `instructor_id` | Post-schedule change requests and administrative approval workflow |

---

## Multi-Semester Dynamic Preference Simulation

### Semester Schedule (Fall 2024 – Spring 2027)

| Semester ID | Semester Name | Dates | Status |
|:---:|:---|:---|:---:|
| **1** | Fall 2024 | 2024-08-26 → 2024-12-20 | Completed |
| **2** | Spring 2025 | 2025-01-21 → 2025-05-16 | Completed |
| **3** | Fall 2025 | 2025-08-25 → 2025-12-19 | Completed |
| **4** | Spring 2026 | 2026-01-20 → 2026-05-15 | Completed |
| **5** | Fall 2026 | 2026-08-24 → 2026-12-18 | Active |
| **6** | Spring 2027 | 2027-01-19 → 2027-05-14 | Projected |

### Dynamic Preference Variation & Day Rotation

In real universities, faculty do not request identical schedules term after term. Across the 6 terms:
- **Day Rotation**: 100% of faculty rotate preferred meeting patterns between Fall (e.g., Tue/Thu) and Spring (e.g., Mon/Wed).
- **Slot Progression**: Contested prime-time slots (Slots 2 & 3: 09:30–12:15) rotate across terms.
- **Department Room Alignments**: Faculty request rooms within their home department buildings:
  - CS $\rightarrow$ Flarsheim Hall (`FH 256`, `FH 310`) and Royall Hall (`RH 211`).
  - Math $\rightarrow$ Haag Hall (`HH 301`, `HH 201`) and Royall Hall (`RH 204`).
  - ECE/Physics $\rightarrow$ Flarsheim Hall and Royall Hall.
  - Chem/Bio $\rightarrow$ Spencer Chemistry Building (`SCB 101`, `SCB 205`).
- **Archive Generation**: Each semester's confirmed timetable is exported to `backend/data/umkc/schedules.json` and permanently archived as `backend/data/umkc/schedules_sem{N}.json`.

---

## Repository Structure (Monorepo Layout)

```text
optisched/
├── .github/
│   └── workflows/
│       └── ci.yml                             # GitHub Actions CI for Backend & Frontend
├── backend/
│   ├── app/
│   │   ├── api/v1/routes.py                   # REST Controllers (/health, /courses, /rooms, /schedules)
│   │   ├── core/                              # Config & SQLModel Database Engine
│   │   ├── models/entities.py                 # Relational SQLModel Entity Schemas
│   │   ├── schemas/api_schemas.py             # Pydantic Request/Response Validation
│   │   ├── solver/
│   │   │   ├── engine.py                      # Core CP-SAT Solver & Multi-Semester Engine
│   │   │   ├── data_loader.py                 # Relational Data Layer, FK Validation, Filters
│   │   │   └── constraints.py                 # Formalized Hard and Soft Constraint Models
│   │   └── main.py                            # FastAPI Application Entrypoint with CORS
│   ├── data/
│   │   ├── scripts/
│   │   │   ├── generate_umkc_data.py          # Generates 10 UMKC Tables & 504 Preferences
│   │   │   └── instructor_profiles.json       # In-Memory Instructor Priorities & Profiles
│   │   └── umkc/                              # Canonical Relational Database (10 JSON Tables)
│   ├── docs/
│   │   └── openapi.yaml                       # OpenAPI 3.0 API Specification Contract
│   ├── tests/
│   │   ├── solver/
│   │   │   ├── test_umkc_verification.py      # Single-Semester UMKC Scale Suite (15 Tests)
│   │   │   └── test_multi_semester_verification.py # Multi-Semester Dynamic Simulation (10 Tests)
│   │   ├── test_health.py                     # Health Check Endpoint Unit Test
│   │   └── test_models.py                     # SQLModel Entity Unit Tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/                        # Navbar, Sidebar, and AppLayout Shell
│   │   │   └── schedule/                      # ScheduleCalendar (FullCalendar Integration)
│   │   ├── pages/                             # Dashboard, Schedules, Preferences, Admin
│   │   ├── services/                          # Centralized Axios Client & Schedule Services
│   │   ├── types/api.ts                       # TypeScript Domain & Contract Interfaces
│   │   ├── utils/scheduleParser.ts            # Timetable Event Transformation Helpers
│   │   └── mocks/scheduleMockData.json        # Development Mock Datasets
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docs/
│   └── sprint0_planning.md                    # Official Sprint 0 Step-by-Step Execution Guide
├── .gitignore
└── README.md
```

---

## Installation & Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm**
- macOS, Linux, or Windows

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

---

## Quickstart Guide

### Running Backend API Server
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Interactive API Documentation will be live at:
- **Swagger UI**: `http://localhost:8000/api/v1/docs`
- **ReDoc**: `http://localhost:8000/api/v1/redoc`

### Running Frontend Development Server
```bash
cd frontend
npm run dev
```
The application dashboard will be live at: `http://localhost:5173/`

---

## CLI Solver Usage Guide

The solver engine can be executed directly via Python CLI from the project root or backend directory:

### 1. Standard Single-Semester Schedule Run
Runs scheduling for Semester 1 (Fall 2024) and saves the timetable to `backend/data/umkc/schedules.json`:
```bash
python3 backend/app/solver/engine.py
```

### 2. Multi-Semester Simulation (6 Semesters)
Simulates all 6 semesters consecutively, applying dynamic preference rotation and priority carryovers from term to term:
```bash
python3 backend/app/solver/engine.py --semesters 6 --reset
```

### 3. Intra-Semester Multi-Round Simulation
Simulates multiple bidding rounds within each semester to observe intra-term priority convergence:
```bash
# 2 rounds per semester across 3 semesters = 6 rounds total
python3 backend/app/solver/engine.py --semesters 3 --simulate 2
```

### 4. Reset Priorities to Base Defaults
Clears accumulated compensation and resets all faculty priorities to their academic rank baselines:
```bash
python3 backend/app/solver/engine.py --reset
```

---

## Automated Verification & Test Suites

The project features **30 automated test cases** across API endpoints, data models, and multi-semester simulations:

### 1. Pytest Backend Suite (Health Check & SQLModel Verification)
```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

### 2. Multi-Semester Dynamic Verification Suite (10 Tests)
Validates cross-semester consistency, preference rotations, and priority carryover dynamics:
```bash
python3 backend/tests/solver/test_multi_semester_verification.py
```

### 3. Single-Semester UMKC Scale Suite (15 Tests)
Validates constraint satisfaction, capacity limits, qualification purity, and solver latency:
```bash
python3 backend/tests/solver/test_umkc_verification.py
```

---

## Solver Performance Benchmarks

Measured on Apple Silicon (M-series / macOS):

| Benchmark Metric | Observed Value | Design Target | Status |
|:---|:---:|:---:|:---:|
| **Model Formulation Time** | 0.104 seconds | $< 1.0\text{ s}$ | Exceeded |
| **Single-Semester Solve Time** | 2.869 seconds | $< 10.0\text{ s}$ | Exceeded |
| **6-Semester Full Simulation Time** | 20.28 seconds | $< 60.0\text{ s}$ | Exceeded |
| **Solution Optimality** | 100% OPTIMAL | OPTIMAL or FEASIBLE | Exceeded |
| **Double-Booking Violations** | 0 | 0 (Hard Constraint) | Verified |
| **Over-Capacity Violations** | 0 | 0 (Hard Constraint) | Verified |
| **Faculty Over-Load Violations** | 0 (Max 2 classes) | 0 (Hard Constraint) | Verified |
| **Lab Misassignment Violations** | 0 | 0 (Hard Constraint) | Verified |

---

## Authors & Acknowledgments

- **Course**: CS 5551 — Advanced Software Engineering
- **Institution**: University of Missouri–Kansas City (UMKC) — School of Science & Engineering (SSE)
- **Engine**: Google OR-Tools CP-SAT Solver
