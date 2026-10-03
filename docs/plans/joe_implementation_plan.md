# Sprint 1 Individual Implementation Plan: Joe Doan

**Name:** Joe Doan  
**Role:** Project Coordinator & Algorithm / Solver Integration Lead  
**Assigned User Stories:** US-1, US-2  
**Assigned Acceptance Criteria:** AC 1.1, AC 1.2, AC 2.1, AC 2.2, AC 2.3  
**Target LOC:** 480+ Lines of Code (Production + Automated Tests)  
**Branch:** `feature/joe-solver-seeder-api`  

---

## 1. Domain Ownership & Responsibilities

In Sprint 0, Joe migrated the Google OR-Tools CP-SAT prototype and verified all 25 UMKC scale tests.  
In **Sprint 1**, Joe's primary objective is to **bridge the solver engine with the production database and FastAPI endpoints**:
1. Build a **Database Seeding Service** to populate the SQLite database with real UMKC records from `backend/data/umkc/*.json`.
2. Build a **Solver Execution Service** that reads live database entities, runs the CP-SAT optimization model, transforms the output into `Schedule` entities, and persists them into the database.
3. Expose REST endpoints: `POST /api/v1/solver/run` and `POST /api/v1/admin/seed`.
4. Author comprehensive Pytest integration tests to verify database seeding idempotency and solver API execution.
5. Coordinate the Sprint 1 team meetings, log Meeting Minutes on Asana, and organize the 5-Minute Demonstration Video.

---

## 2. Step-by-Step Task Checklist

```
[ ] Step 1: Create Git Branch 'feature/joe-solver-seeder-api'
[ ] Step 2: Implement Database Seeder ('backend/app/core/seeder.py')
[ ] Step 3: Implement Solver Bridge Service ('backend/app/services/solver_service.py')
[ ] Step 4: Implement Solver API Endpoints ('backend/app/api/v1/routes_solver.py')
[ ] Step 5: Mount Routes in 'backend/app/main.py'
[ ] Step 6: Write Automated Tests ('backend/tests/test_seeder.py' & 'backend/tests/test_solver_api.py')
[ ] Step 7: Verify 100% Test Pass Rate with Pytest
[ ] Step 8: Document Meeting Minutes & Lead Video Demo Recording
```

---

## 3. Detailed Technical Implementation

### Task 1: Database Seeding Service (`backend/app/core/seeder.py`)
* **File Location:** `backend/app/core/seeder.py` (~130 LOC)
* **Purpose:** Read JSON tables from `backend/data/umkc/` and load them into SQLite tables using SQLModel.
* **Key Functions to Write:**
  ```python
  def seed_database(data_dir: str = "backend/data/umkc", force_reset: bool = False) -> dict:
      """
      Reads users.json, courses.json, rooms.json, semesters.json, 
      time_slots.json, instructor_preferences.json.
      Inserts records into SQLite via Session(engine).
      Ensures idempotency: checks if records already exist before inserting.
      Returns summary dict: {"users": 20, "courses": 40, "rooms": 12, ...}
      """
  ```
* **Acceptance Mapping:** Satisfies **AC 1.1** (20 users, 40 courses, 12 rooms, 6 semesters, 6 time slots seeded) and **AC 1.2** (idempotency: running twice does not duplicate records).

### Task 2: Solver Bridge Service (`backend/app/services/solver_service.py`)
* **File Location:** `backend/app/services/solver_service.py` (~170 LOC)
* **Purpose:** Extract data from the database session, format it for the CP-SAT solver, run `build_schedule_model()` from `backend/app/solver/engine.py`, and save generated schedules into the `schedules` table.
* **Key Functions to Write:**
  ```python
  def run_solver_for_semester(semester_id: int, session: Session) -> dict:
      """
      1. Validates semester_id exists in database. If not, raises HTTPException(404).
      2. Queries courses, rooms, instructor preferences for the given semester.
      3. Constructs solver profile structures.
      4. Invokes build_schedule_model() and solver.Solve().
      5. If INFEASIBLE: raises HTTPException(422, detail="Solver could not find feasible schedule").
      6. If OPTIMAL/FEASIBLE:
         - Clears existing tentative schedules for semester_id.
         - Iterates through solver assignments and inserts Schedule entities:
           Schedule(semester_id=semester_id, course_id=c_id, user_id=u_id, room_id=r_id, time_slot_id=t_id, status='confirmed')
         - Updates instructor priority_scores in User table based on preference satisfaction.
         - session.commit()
      7. Returns: {
             "status": "OPTIMAL",
             "semester_id": semester_id,
             "scheduled_count": 40,
             "wall_time_seconds": solve_time,
             "satisfaction_score": objective_val
         }
      """
  ```
* **Acceptance Mapping:** Satisfies **AC 2.1** (generates and persists schedule) and **AC 2.3** (infeasible diagnostics).

### Task 3: Solver & Admin API Endpoints (`backend/app/api/v1/routes_solver.py`)
* **File Location:** `backend/app/api/v1/routes_solver.py` (~90 LOC)
* **Endpoints:**
  * `POST /api/v1/solver/run`
    * Body: `{"semester_id": 1}`
    * Returns: `200 OK` with solver execution metrics or `404/422`.
  * `POST /api/v1/admin/seed`
    * Query param: `force: bool = False`
    * Returns: `200 OK` with seeded entity counts.
* **Acceptance Mapping:** Satisfies **AC 2.1, AC 2.2, AC 1.1**.

### Task 4: Automated Pytest Suite
* **Files to Create:**
  * `backend/tests/test_seeder.py` (~80 LOC)
    * `test_seed_initial_database()`: Verifies exact table counts (20 users, 40 courses, 12 rooms).
    * `test_seeder_idempotency()`: Runs `seed_database()` twice; asserts count remains equal.
  * `backend/tests/test_solver_api.py` (~110 LOC)
    * `test_solver_run_success()`: Calls `POST /api/v1/solver/run` with semester 1; asserts status `"OPTIMAL"`, count 40, and checks DB table `schedules`.
    * `test_solver_run_invalid_semester()`: Calls `POST /api/v1/solver/run` with semester 999; asserts HTTP 404.
    * `test_solver_persists_schedule_records()`: Queries `/api/v1/schedules?semester_id=1` after solve; asserts non-empty array of events returned.

> **Note on Existing Solver Tests:** The Sprint 0 verification suites (`test_umkc_verification.py`, `test_multi_semester_verification.py`) are standalone Python scripts run via `python tests/solver/test_xxx.py`, not Pytest-collected tests. In Sprint 1, Joe should consider wrapping key solver assertions as proper Pytest functions so they appear in the unified `pytest backend/tests/ -v` output for the video demo.

---

## 4. LOC Contribution Breakdown for Joe

| File | Type | Purpose | LOC Estimate |
| :--- | :--- | :--- | :---: |
| `backend/app/core/seeder.py` | Production | Database seeding script from JSON tables | ~130 |
| `backend/app/services/solver_service.py` | Production | Bridge between ORM and CP-SAT engine | ~170 |
| `backend/app/api/v1/routes_solver.py` | Production | Solver run and database seed endpoints | ~90 |
| `backend/tests/test_seeder.py` | Test | Seeder integration & idempotency tests | ~80 |
| `backend/tests/test_solver_api.py` | Test | Solver API execution and persistence tests | ~110 |
| **Total LOC Expected** | | | **~580 LOC** (Compliant: > 400 LOC) |

---

## 5. Verification Commands

Run the following commands to verify implementation correctness:
```bash
# 1. Activate virtual environment
source backend/venv/bin/activate

# 2. Seed database
python -m app.core.seeder

# 3. Run new automated tests
pytest backend/tests/test_seeder.py backend/tests/test_solver_api.py -v

# 4. Verify all backend tests pass
pytest backend/tests/ -v
```

---

## 6. Video Demonstration Coordination
Joe will present **Segment 1** (0:00 - 0:45) introducing the project architecture and **Segment 5** (4:00 - 5:00) running the live automated test suites on terminal.
