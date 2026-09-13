# OptiSched: Sprint 0 Step-by-Step Onboarding and Execution Guide

This document establishes the official technical foundation, workflow rules, and individual step-by-step responsibilities for **OptiSched (Smart Event Scheduling System)** during **Sprint 0: Up-front Planning**. All guidelines comply with the curriculum standards of CS 5551 Advanced Software Engineering.

---

## 1. Project Objectives & Academic Governance

OptiSched automates the academic course and room scheduling workflow between Course Coordinators and Academic Instructors. The system replaces ad-hoc scheduling by formulating schedule creation as a constraint satisfaction and optimization problem (Hard and Soft constraints).

| Academic Mandate | Compliance Strategy & Enforcement |
| :--- | :--- |
| **Individual 400+ LOC Baseline** | Every student must author at least 400 lines of code (LOC), spanning production code and automated test code. Passive participation or documentation-only roles receive zero individual project credit. |
| **Buddy Rating System** | Peer evaluation ratings (scale 0.0 to 1.0) directly scale each member's final project score. A rating below 0.8 significantly lowers the individual score unless isolated by peer consensus rules. |
| **Working Software & Tests** | Progress is judged exclusively by working, fully tested software increments. Automated unit testing, acceptance test verification, and measurable code coverage are required for every sprint increment. |
| **Sprint 0 Goal (Week 5)** | Sprint 0 focuses on architectural planning, tech stack decisions, development environment setup, coding style guides, baseline repository configuration, and migration of existing prototype code into the production monorepo. |

---

## 2. Sprint 0 Scope Definition

Sprint 0 is a **planning and foundation sprint** — not an implementation sprint. The deliverables are:

| Category | Deliverables |
| :--- | :--- |
| **Repository & DevOps** | Monorepo structure, branch protection, CI pipeline config, `.env` templates |
| **Architecture Documentation** | System architecture diagram, constraint formulation document, ERD |
| **API Contract** | OpenAPI/Swagger specification for all `/api/v1/` endpoints (draft) |
| **Boilerplate & Scaffolding** | Project skeletons for `/backend` and `/frontend` with dependency manifests |
| **Existing Code Migration** | Port proven solver prototype and dataset pipeline into monorepo structure |
| **Testing Infrastructure** | Test runners configured (Pytest + Vitest), initial smoke tests passing |
| **Sprint 0 Report** | Planning report per CS 5551 requirements |

> **Note:** Full CRUD implementation, complete UI pages, and production features are **Sprint 1+** scope. Sprint 0 produces the scaffolding and contracts that Sprint 1 builds upon.

---

## 3. Team Role & Work Allocation Matrix

| Member & Role | Domain Ownership | Sprint 0 Deliverables | LOC Accumulation Strategy |
| :--- | :--- | :--- | :--- |
| **Joe** *(Coordinator / Algorithm)* | Constraint Optimization Engine (Google OR-Tools CP-SAT), Architecture, Project Coordination. | Migrate existing solver into monorepo; define constraint matrix with code stubs; setup repo & branch rules; author Sprint 0 report; run team meetings. | Solver module migration, constraint model interfaces, type-annotated function stubs, solver unit test scaffolding, benchmark test migration. |
| **Tony** *(Backend Engineer)* | FastAPI Server, Relational Database (SQLModel/SQLAlchemy), REST Endpoints, Migrations. | Initialize FastAPI boilerplate; convert ERD to ORM model stubs; setup database connection config; draft OpenAPI spec; configure Pytest runner. | ORM model definitions, Pydantic validation schemas, API route stubs, health check endpoint, Pytest fixture setup. |
| **Tina** *(Frontend Engineer)* | Core Application Layout, Routing, Course/Room Management Forms, Instructor Preferences View. | Initialize React+Vite project; configure Tailwind CSS; implement navigation shell skeleton; setup Vitest runner. | Layout component scaffolding, route configuration, Tailwind theme tokens, Vitest component test stubs. |
| **Sal** *(Frontend Engineer)* | Interactive Schedule Matrix, Calendar View (FullCalendar), API Client Layer, State Store. | Integrate FullCalendar library; construct mock JSON schedule data; build API service abstraction skeleton; setup UI test runner. | Calendar component skeleton, mock data structures, API client base config, type interfaces, calendar test stubs. |

---

## 4. Shared Team Task: API Contract Definition

Before any individual coding begins, the full team must collaborate to define the API contract that connects the frontend to the backend.

| Step | Owner | Action |
| :--- | :--- | :--- |
| 1. Draft endpoint list | Tony + Joe | List all REST endpoints (`/api/v1/courses`, `/api/v1/schedules`, `/api/v1/preferences`, etc.) with HTTP methods, request/response schemas, and status codes. |
| 2. Review & validate | Tina + Sal | Confirm that the API contract covers all data the frontend components need (preference form fields, calendar event shape, filter parameters). |
| 3. Publish spec | Tony | Commit finalized OpenAPI spec to `/backend/docs/openapi.yaml`. |
| 4. Generate types | Sal | Generate TypeScript interfaces from OpenAPI spec into `/frontend/src/types/api.ts`. |

> **This contract is the single source of truth.** Frontend and backend work independently against this spec from Sprint 1 onward.

---

## 5. Individual Step-by-Step Execution Guides

### 5.1. Guide for Joe (Architecture & Constraint Engine)

**Objective:** Establish repository infrastructure, migrate the existing proven solver prototype into the monorepo, and document the constraint formulation as code-level interfaces.

1. **Step 1: Repository & Git Workflow Configuration**
   * Initialize GitHub repository under monorepo structure (`/backend` and `/frontend`).
   * Configure branch protection rules on `main` and `dev` (require PR review approval, disallow direct push).
   * Create `.github/workflows/ci.yml` with Pytest and Vitest runners for automated CI on pull requests.

2. **Step 2: Existing Solver Migration**
   * Port `adv_software_scheduler_project.py` into `/backend/app/solver/engine.py`, refactoring into modular functions (e.g., `build_model()`, `add_hard_constraints()`, `add_soft_constraints()`, `solve()`).
   * Port `data_loader.py` into `/backend/app/solver/data_loader.py`, preserving semester-aware loading and relational integrity checks.
   * Migrate the UMKC dataset (`data/umkc/`) into `/backend/data/umkc/`.

3. **Step 3: Constraint Formulation Document (as Code)**
   * In `/backend/app/solver/constraints.py`, define typed dataclasses or Pydantic models for: `HardConstraint` (room capacity, time overlap prevention, max 2 classes per instructor) and `SoftConstraint` (instructor time preference, room preference).
   * Write docstrings documenting the mathematical formulation (variables, domains, objective function) directly in the solver module.

4. **Step 4: Test Migration & Solver Smoke Tests**
   * Migrate `test_umkc_verification.py` (15 tests) and `test_multi_semester_verification.py` (10 tests) into `/backend/tests/solver/`.
   * Verify all 25 tests pass in the new directory structure via `pytest backend/tests/ -v`.

5. **Step 5: Coordinator Responsibilities**
   * Organize weekly team meetings, record Meeting Minutes.
   * Monitor Asana/Jira task tracking and compile the official Sprint 0 Planning Report.

---

### 5.2. Guide for Tony (Backend Engineer)

**Objective:** Deliver a functional FastAPI backend boilerplate with ORM model stubs, database configuration, and a published API contract.

1. **Step 1: Environment Setup**
   * Navigate to `/backend`.
   * Create Python virtual environment: `python -m venv venv`.
   * Create `requirements.txt` containing: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `pydantic`, `ortools`, `pytest`, `pytest-cov`, `flake8`, `black`.
   * Create `.env.example` with database connection string templates.

2. **Step 2: Database Schema & ORM Model Stubs**
   * In `app/models/`, implement relational model definitions using SQLModel: `User` (Admin, Coordinator, Instructor), `Course`, `Room`, `TimeSlot`, `InstructorPreference`, `Schedule`, and `EditRequest`.
   * Create database engine session manager in `app/core/database.py` supporting SQLite for local development.
   * **Note:** Full CRUD operations are Sprint 1 scope. Sprint 0 only defines the schema.

3. **Step 3: API Route Stubs & Health Check**
   * In `app/main.py`, initialize FastAPI instance with CORS middleware allowing local frontend ports.
   * Create endpoint `GET /api/v1/health` returning `{"status": "healthy", "timestamp": "..."}`.
   * Create **stub routers** (returning placeholder responses) for `/api/v1/courses`, `/api/v1/rooms`, `/api/v1/preferences`, `/api/v1/schedules` to match the API contract.

4. **Step 4: OpenAPI Specification Draft**
   * Author `/backend/docs/openapi.yaml` defining all endpoint paths, request/response schemas, and error codes.
   * Coordinate with Tina and Sal to validate the spec covers frontend data requirements.

5. **Step 5: Testing Infrastructure**
   * In `tests/test_health.py`, implement unit test verifying the health endpoint status code and payload.
   * In `tests/test_models.py`, test database session fixtures and model instantiation.
   * Ensure execution via `pytest --cov=app tests/` with 100% pass rate.

---

### 5.3. Guide for Tina (Frontend: Shell, Routing & Styling)

**Objective:** Deliver a structured React application shell with client routing, design system configuration, and testing infrastructure ready for Sprint 1 feature development.

1. **Step 1: Project Initialization & Styling**
   * Navigate to `/frontend`.
   * Scaffold project: `npm create vite@latest . -- --template react-ts`.
   * Install dependencies: `npm install react-router-dom lucide-react clsx tailwindcss postcss autoprefixer`.
   * Initialize Tailwind CSS configuration (`tailwind.config.js`) with OptiSched brand colors, and apply styling directives to `src/index.css`.

2. **Step 2: Design System & Theme Tokens**
   * Define color palette, typography scale, spacing tokens, and component variants in Tailwind config.
   * Create `src/styles/` directory with shared CSS utility classes and animation keyframes.
   * Establish dark/light mode support via Tailwind's `darkMode` configuration.

3. **Step 3: Application Layout Shell & Page Routing**
   * In `src/components/layout/`, build responsive `Navbar`, `Sidebar`, and `AppLayout` wrapper components.
   * In `src/App.tsx`, configure route definitions for: Dashboard (`/`), Preferences (`/preferences`), Master Schedule (`/schedule`), and Admin Management (`/admin`).
   * Each page renders a **placeholder component** (e.g., `<h1>Preferences Page — Coming in Sprint 1</h1>`). Full page content is Sprint 1 scope.

4. **Step 4: Frontend Testing Infrastructure (Vitest)**
   * Install testing tools: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`.
   * Configure `vitest.config.ts` with jsdom environment and path aliases.
   * Write smoke test in `src/components/layout/__tests__/Navbar.test.tsx` verifying branding text renders.
   * Write route test in `src/App.test.tsx` verifying all route paths resolve without errors.

---

### 5.4. Guide for Sal (Frontend: Schedule Matrix & API Layer)

**Objective:** Deliver the calendar visualization skeleton, mock data structures, and a standardized API communication layer ready for Sprint 1 integration.

1. **Step 1: Calendar Library Integration**
   * Install calendar engine: `npm install @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction`.
   * Create `src/components/schedule/ScheduleCalendar.tsx` rendering an empty weekly time grid (Monday to Friday, 08:00 to 21:00).
   * Style the calendar container to fit within Tina's `AppLayout` shell.

2. **Step 2: TypeScript Interfaces & Mock Data**
   * In `src/types/`, define TypeScript interfaces matching the API contract: `Course`, `Room`, `TimeSlot`, `InstructorPreference`, `ScheduleEvent`, etc.
   * Construct `src/mocks/scheduleMockData.json` containing structured schedule records (course codes, sections, assigned rooms, instructors, color tags).
   * Implement parser in `src/utils/scheduleParser.ts` transforming raw API response models into FullCalendar event objects.

3. **Step 3: Centralized API Service Layer**
   * Install Axios: `npm install axios`.
   * Create `src/services/apiClient.ts` with base URL from environment variable, timeout settings, and global response error interceptors.
   * Create **stub** service modules: `src/services/scheduleService.ts` and `src/services/preferenceService.ts` that currently return mock data but are structured for real API calls in Sprint 1.

4. **Step 4: Calendar Component Testing**
   * In `src/components/schedule/__tests__/ScheduleCalendar.test.tsx`, write test verifying the calendar grid mounts and renders the correct weekday headers.
   * Write test verifying mock schedule events display in the correct time slots.
   * Verify error states render gracefully when the API service returns network failures.

---

## 6. Architectural Standards & Code Conventions

### 6.1. Directory Structure Specification

```text
optisched/
├── .github/
│   └── workflows/          # GitHub Actions CI for pytest and vitest
├── backend/
│   ├── app/
│   │   ├── api/            # API Route Controllers (v1)
│   │   ├── core/           # Config, database engine, security
│   │   ├── models/         # Relational entity schemas (SQLModel)
│   │   ├── schemas/        # Pydantic request/response validation
│   │   ├── services/       # Business logic & ORM operations
│   │   └── solver/         # OR-Tools constraint satisfaction algorithms
│   ├── data/
│   │   └── umkc/           # UMKC dataset (10 JSON tables, 6 semesters)
│   ├── docs/
│   │   └── openapi.yaml    # API contract specification
│   ├── tests/
│   │   ├── solver/         # Solver verification tests (25 tests)
│   │   ├── test_health.py
│   │   └── test_models.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/     # Reusable layout & UI components
    │   ├── pages/          # Dashboard, Preferences, Schedule views
    │   ├── services/       # Axios API client handlers
    │   ├── types/          # TypeScript domain interfaces
    │   ├── utils/          # Data parsers and helpers
    │   ├── styles/         # Shared CSS utilities and tokens
    │   └── mocks/          # Mock JSON datasets for development
    ├── package.json
    ├── vitest.config.ts
    └── vite.config.ts
```

### 6.2. Code Style & Quality Rules

| Area | Standard |
| :--- | :--- |
| **Python** | `black` formatter (line length 88), `flake8` linter, type hints required on all public functions |
| **TypeScript** | `eslint` + `prettier`, strict mode enabled, no `any` types in production code |
| **Git Commits** | Conventional Commits format: `feat:`, `fix:`, `docs:`, `test:`, `chore:` |
| **Branch Strategy** | `main` → production, `dev` → integration, `feature/<name>` → individual work |
| **PR Rules** | Minimum 1 reviewer approval, all CI checks passing, no direct push to `main` or `dev` |

### 6.3. Sprint 0 → Sprint 1 Handoff Checklist

Before Sprint 0 is marked complete, the following must be verified:

- [ ] Monorepo structure matches Section 6.1 directory spec
- [ ] All branch protection rules active on GitHub
- [ ] CI pipeline runs Pytest + Vitest on every PR
- [ ] OpenAPI spec committed and reviewed by all 4 members
- [ ] FastAPI health endpoint returns 200 OK
- [ ] React app renders navigation shell with all routes
- [ ] FullCalendar renders empty weekly grid
- [ ] All existing solver tests (25) pass in new directory structure
- [ ] Sprint 0 Planning Report submitted
