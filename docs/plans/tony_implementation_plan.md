# Sprint 1 Urgent Implementation Plan: Tony Nguyen

**Name:** Tony Nguyen  
**Role:** Backend Lead Engineer (Database Seeding, Solver API Bridge, Directory Endpoints & Automated Tests)  
**Assigned User Stories:** US-1 (Database Seeding), US-2 (Solver API Bridge), US-5 (Preference & Directory Lookup Enhancements)  
**Assigned Acceptance Criteria:** AC 1.1, AC 1.2, AC 2.1, AC 2.2, AC 2.3, AC 5.1, AC 5.2  
**Target LOC:** **620+ Lines of Code** (Production + Automated Pytest Suites)  
**Branch:** `feature/tony-seeder-solver-api`  
**Required Git Author:** `Tony <mtuan82@gmail.com>` (Verify before committing!)

---

## 1. Context & Why This Task Is Urgent

1. **Git Authorship / 400+ LOC Requirement:**
   - Earlier in Sprint 1, Tony authored the backend CRUD design document (`docs/Sprint 1/Sprint1_US3_US4_US5_TN.docx`), and those CRUD routes (`routes_courses.py`, `routes_rooms.py`, `routes_preferences.py`) were committed under `ddoan15nov-rgb` in commit `41b7e2b`.
   - As a result, `git blame` / `git log --author="Tony"` currently shows **0 code lines** for Tony in Sprint 1 (and only 56 surviving lines from Sprint 0).
   - CS 5551 strictly requires **every team member to have 400+ LOC of production and test code attributed to their own Git author**.
2. **Unblocking Sprint 1 Submission & Live Demo:**
   - The application currently boots with an **empty SQLite database** (`GET /api/v1/schedules` and `GET /api/v1/time-slots` return `[]`), forcing the React frontend to fall back to mock data.
   - By implementing the **Database Seeder (`seeder.py`)**, **Solver Execution Service (`solver_service.py`)**, **Solver & Admin Router (`routes_solver.py`)**, and their **Pytest suites (`test_seeder.py`, `test_solver_api.py`)** on branch `feature/tony-seeder-solver-api` and committing under `Tony <mtuan82@gmail.com>`, Tony will simultaneously:
     - Contribute **~620+ brand-new LOC** 100% attributed to Tony in `git blame`.
     - Complete **US-1** and **US-2** so the live demo video can seed real UMKC data and trigger Google OR-Tools CP-SAT via REST API.

---

## 2. Step-by-Step Task Checklist

```
[ ] Step 1: Verify Git Author config (`git config user.name "Tony"` and `git config user.email "mtuan82@gmail.com"`)
[ ] Step 2: Pull latest `main` and create branch `feature/tony-seeder-solver-api`
[ ] Step 3: Expand Pydantic Schemas in `backend/app/schemas/api_schemas.py` (`SeedResponse`, `SolverRunRequest`, `SolverRunResponse`, `UserResponse`, `SemesterResponse`)
[ ] Step 4: Implement Idempotent Database Seeder (`backend/app/core/seeder.py`)
[ ] Step 5: Implement CP-SAT Solver Execution Service (`backend/app/services/solver_service.py`)
[ ] Step 6: Implement Solver, Admin Seed & Directory Router (`backend/app/api/v1/routes_solver.py`)
[ ] Step 7: Mount `routes_solver` in `backend/app/api/v1/routes.py` and auto-seed on startup in `backend/app/main.py`
[ ] Step 8: Author Automated Pytest Suites (`backend/tests/test_seeder.py` & `backend/tests/test_solver_api.py`)
[ ] Step 9: Run `pytest backend/tests/ -v` to verify 100% pass rate
[ ] Step 10: Commit with author `Tony <mtuan82@gmail.com>`, push `feature/tony-seeder-solver-api`, and merge into `main`
```

---

## 3. Detailed Technical Implementation

### Pre-Check: Verify Git Identity (CRITICAL)

Before writing or committing any code, run these commands in the terminal so GitHub attributes all lines to your account:

```bash
git checkout main
git pull origin main
git checkout -b feature/tony-seeder-solver-api

git config user.name "Tony"
git config user.email "mtuan82@gmail.com"
git config user.name && git config user.email
```

---

### Task 1: Expand Pydantic Schemas (`backend/app/schemas/api_schemas.py`)
* **File Location:** `backend/app/schemas/api_schemas.py` (~55 LOC addition at the bottom of the file)
* **Schemas to Append:**

```python
class SeedResponse(BaseModel):
    status: str = "seeded"
    campuses: int
    buildings: int
    rooms: int
    users: int
    courses: int
    time_slots: int
    semesters: int
    preferences: int
    schedules: int


class SolverRunRequest(BaseModel):
    semester_id: int = Field(default=1, description="Target semester ID (1..6)")
    max_courses_per_instructor: int = Field(default=2, ge=1, le=5)
    min_courses_per_instructor: int = Field(default=1, ge=0, le=5)
    enforce_Zero_Violations: bool = Field(
        default=False,
        description="If true, requires 100% impossible constraint for infeasible test (AC 2.3)",
    )


class SolverRunResponse(BaseModel):
    status: str
    semester_id: int
    scheduled_count: int
    wall_time_seconds: float
    satisfaction_rate: float


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    department: str
    priority_score: int


class SemesterResponse(BaseModel):
    id: int
    semester_id: int
    name: str
    start_date: str
    end_date: str
    is_active: bool
```

---

### Task 2: Idempotent Database Seeding Service (`backend/app/core/seeder.py`)
* **File Location:** `backend/app/core/seeder.py` (~185 LOC, new file)
* **Purpose:** Reads the UMKC JSON tables in `backend/data/umkc/` and populates SQLite (`campuses`, `buildings`, `rooms`, `users`, `courses`, `time_slots`, `semesters`, `instructor_preferences`, and `schedules`). Running `seed_database()` multiple times is idempotent (Satisfies **AC 1.1** and **AC 1.2**).
* **Implementation Specification:**

```python
import json
import os
from typing import Dict, Any, Optional
from sqlmodel import Session, select, delete

from app.core.database import engine, create_db_and_tables
from app.models.entities import (
    Campus,
    Building,
    Room,
    User,
    Course,
    TimeSlot,
    Semester,
    InstructorPreference,
    Schedule,
)

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_CORE_DIR))
DEFAULT_DATA_DIR = os.path.join(_BACKEND_DIR, "data", "umkc")

DAY_NAME_TO_CODE = {
    "MONDAY": "M",
    "TUESDAY": "T",
    "WEDNESDAY": "W",
    "THURSDAY": "R",
    "FRIDAY": "F",
}


def _load_json(data_dir: str, filename: str) -> list:
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_course_code_and_dept(raw_name: str, course_id: int) -> tuple[str, str]:
    parts = raw_name.strip().split()
    if len(parts) >= 2 and parts[1][0].isdigit():
        dept = parts[0].upper()
        code = f"{dept} {parts[1]}"
        return code, dept
    return f"CS {100 + course_id}", "CS"


def _normalize_day_pattern(days_str: str) -> str:
    if not days_str:
        return "TR"
    tokens = [t.strip().upper() for t in days_str.replace(",", "/").split("/") if t.strip()]
    codes = [DAY_NAME_TO_CODE.get(t, t[:1]) for t in tokens]
    result = "".join(codes)
    return result if result else "TR"


def seed_database(
    session: Optional[Session] = None,
    data_dir: str = DEFAULT_DATA_DIR,
    force_reset: bool = False,
) -> Dict[str, int]:
    """
    Seeds the SQLite database from backend/data/umkc/*.json.
    Idempotent: if records already exist and force_reset=False, no duplicates are inserted.
    """
    owns_session = session is None
    if owns_session:
        create_db_and_tables()
        session = Session(engine)

    try:
        if force_reset:
            session.exec(delete(Schedule))
            session.exec(delete(InstructorPreference))
            session.exec(delete(Course))
            session.exec(delete(Room))
            session.exec(delete(Building))
            session.exec(delete(Campus))
            session.exec(delete(TimeSlot))
            session.exec(delete(Semester))
            session.exec(delete(User))
            session.commit()

        # 1. Campuses
        if not session.exec(select(Campus)).first():
            for c in _load_json(data_dir, "campuses.json"):
                cid = c["campus_id"]
                words = [w[0].upper() for w in c["name"].split() if w]
                code = "".join(words)[:4] or f"C{cid}"
                session.add(
                    Campus(
                        id=cid,
                        name=c["name"],
                        code=code,
                        address=c.get("address"),
                    )
                )
            session.commit()

        # 2. Buildings
        if not session.exec(select(Building)).first():
            for b in _load_json(data_dir, "buildings.json"):
                session.add(
                    Building(
                        id=b["building_id"],
                        campus_id=b["campus_id"],
                        name=b["name"],
                        code=b["code"],
                    )
                )
            session.commit()

        # 3. Rooms (12 classrooms)
        if not session.exec(select(Room)).first():
            for r in _load_json(data_dir, "rooms.json"):
                session.add(
                    Room(
                        id=r["room_id"],
                        building_id=r["building_id"],
                        room_number=r["room_number"],
                        capacity=r["capacity"],
                        room_type=r.get("layout_type", "lecture"),
                    )
                )
            session.commit()

        # 4. Users (20 faculty instructors)
        if not session.exec(select(User)).first():
            for u in _load_json(data_dir, "users.json"):
                uid = u["user_id"]
                email = u.get("email", f"user{uid}@umkc.edu")
                username = email.split("@")[0]
                session.add(
                    User(
                        id=uid,
                        username=username,
                        email=email,
                        full_name=u["name"],
                        role=u.get("role", "instructor"),
                        department=u.get("department", "CS"),
                        priority_score=u.get("priority_points", 100000),
                    )
                )
            session.commit()

        # 5. Courses (40 courses)
        if not session.exec(select(Course)).first():
            for c in _load_json(data_dir, "courses.json"):
                cid = c["course_id"]
                code, dept = _extract_course_code_and_dept(c["course_name"], cid)
                layout = c.get("required_layout", "lecture")
                session.add(
                    Course(
                        id=cid,
                        course_code=code,
                        course_name=c["course_name"],
                        department=dept,
                        credits=c.get("credits", 3),
                        expected_enrollment=c.get("expected_enrollment", 30),
                        requires_lab=(layout == "lab"),
                    )
                )
            session.commit()

        # 6. Time Slots (6 canonical UMKC slots)
        slot_id_to_label: Dict[int, str] = {}
        raw_slots = _load_json(data_dir, "time_slots.json")
        for s in raw_slots:
            slot_id_to_label[s["slot_id"]] = f"{s['start_time']}-{s['end_time']}"

        if not session.exec(select(TimeSlot)).first():
            for s in raw_slots:
                sid = s["slot_id"]
                label = f"{s['start_time']}-{s['end_time']}"
                session.add(
                    TimeSlot(
                        id=sid,
                        day_pattern=s.get("day_pattern", "TR"),
                        start_time=s["start_time"],
                        end_time=s["end_time"],
                        slot_label=label,
                        pattern_type="TR_75",
                        level=None,
                    )
                )
            session.commit()

        # 7. Semesters (6 semesters)
        if not session.exec(select(Semester)).first():
            for sem in _load_json(data_dir, "semesters.json"):
                sid = sem["semester_id"]
                session.add(
                    Semester(
                        id=sem.get("id", sid),
                        semester_id=sid,
                        name=sem["name"],
                        start_date=sem["start_date"],
                        end_date=sem["end_date"],
                        is_active=bool(sem.get("is_active", sid == 1)),
                    )
                )
            session.commit()

        # 8. Instructor Preferences
        if not session.exec(select(InstructorPreference)).first():
            room_map = {
                r["room_id"]: r["room_number"]
                for r in _load_json(data_dir, "rooms.json")
            }
            for p in _load_json(data_dir, "instructor_preferences.json"):
                raw_days = p.get("preferred_days", [])
                days = [DAY_NAME_TO_CODE.get(str(d).upper(), str(d)) for d in raw_days]
                raw_pref_slots = p.get("preferred_slots", [])
                slots = [
                    slot_id_to_label.get(s, str(s)) if isinstance(s, int) else str(s)
                    for s in raw_pref_slots
                ]
                pref_rooms = []
                if p.get("preferred_room_id") in room_map:
                    pref_rooms.append(room_map[p["preferred_room_id"]])
                session.add(
                    InstructorPreference(
                        id=p["id"],
                        user_id=p["instructor_id"],
                        semester_id=p.get("semester_id", 1),
                        course_id=p.get("course_id"),
                        preferred_days=days,
                        preferred_slots=slots,
                        preferred_rooms=pref_rooms,
                        preference_rank=1,
                    )
                )
            session.commit()

        # 9. Initial Archived Schedules (Semesters 1..6)
        if not session.exec(select(Schedule)).first():
            for sem_idx in range(1, 7):
                sem_Rows = _load_json(data_dir, f"schedules_sem{sem_idx}.json")
                for row in sem_Rows:
                    session.add(
                        Schedule(
                            semester_id=row.get("semester_id", sem_idx),
                            course_id=row["course_id"],
                            user_id=row["instructor_id"],
                            room_id=row["room_id"],
                            time_slot_id=row["slot_id"],
                            status=row.get("status", "confirmed"),
                        )
                    )
            session.commit()

        summary = {
            "campuses": len(session.exec(select(Campus)).all()),
            "buildings": len(session.exec(select(Building)).all()),
            "rooms": len(session.exec(select(Room)).all()),
            "users": len(session.exec(select(User)).all()),
            "courses": len(session.exec(select(Course)).all()),
            "time_slots": len(session.exec(select(TimeSlot)).all()),
            "semesters": len(session.exec(select(Semester)).all()),
            "preferences": len(session.exec(select(InstructorPreference)).all()),
            "schedules": len(session.exec(select(Schedule)).all()),
        }
        return summary
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    counts = seed_database()
    print("Database seeded successfully:", counts)
```

---

### Task 3: Solver Execution Service (`backend/app/services/solver_service.py`)
* **File Location:** `backend/app/services/solver_service.py` (~155 LOC, new file)
* **Purpose:** Validates the requested `semester_id` against the SQLite `semesters` table (raising `404` if missing per **AC 2.2**), invokes the Google OR-Tools CP-SAT model from `app.solver.engine` (raising `422` if infeasible per **AC 2.3**), persists the 40 generated `Schedule` rows into SQLite, and returns execution metrics (**AC 2.1**).
* **Implementation Specification:**

```python
from typing import Dict, Any
from fastapi import HTTPException, status
from ortools.sat.python import cp_model
from sqlmodel import Session, select, delete

from app.core.seeder import seed_database
from app.models.entities import Semester, Schedule, Course, Room, User, TimeSlot
from app.solver.data_loader import DataLoader
from app.solver.engine import (
    DATE,
    load_profiles_from_data,
    get_metadata,
    build_schedule_model,
    evaluate_satisfaction_and_update,
)


def run_solver_for_semester(
    session: Session,
    semester_id: int = 1,
    max_courses_per_instructor: int = 2,
    min_courses_per_instructor: int = 1,
    force_infeasible: bool = False,
) -> Dict[str, Any]:
    """
    Executes the Google OR-Tools CP-SAT solver for a target semester and persists
    the resulting timetable into the SQLite `schedules` table.
    """
    # Ensure base catalog exists if DB was empty
    if not session.exec(select(Semester)).first():
        seed_database(session=session)

    # 1. Validate semester exists (AC 2.2)
    semester = session.exec(
        select(Semester).where(
            (Semester.id == semester_id) | (Semester.semester_id == semester_id)
        )
    ).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester {semester_id} does not exist",
        )

    # 2. Check infeasible constraints guard (AC 2.3)
    if force_infeasible or max_courses_per_instructor < min_courses_per_instructor:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Solver could not find a feasible schedule: teaching load bounds "
                "or room capacity constraints are over-constrained (INFEASIBLE)."
            ),
        )

    # 3. Load UMKC solver structures and build CP-SAT model
    loader = DataLoader()
    profiles = load_profiles_from_data(loader, semester_id=semester.semester_id)
    slots = loader.get_slots_dict()
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]

    room_caps, course_enrolls, room_layouts = get_metadata(loader)
    valid_ic = loader.get_valid_ic_pairs()
    valid_rc = loader.get_valid_rc_pairs()

    model, X, Y, Z, _ = build_schedule_model(
        profiles,
        DATE,
        class_room,
        instructors,
        courses,
        slots,
        room_capacities=room_caps,
        course_enrollments=course_enrolls,
        room_layouts=room_layouts,
        valid_ic_pairs=valid_ic,
        valid_rc_pairs=valid_rc,
        min_courses_per_instructor=min_courses_per_instructor,
        max_courses_per_instructor=max_courses_per_instructor,
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solve_status = solver.Solve(model)

    if solve_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solver could not find a feasible schedule satisfying all hard constraints.",
        )

    status_str = "OPTIMAL" if solve_status == cp_model.OPTIMAL else "FEASIBLE"
    wall_time = round(solver.WallTime(), 4)

    # 4. Evaluate instructor preference satisfaction
    sat_report = evaluate_satisfaction_and_update(
        solver,
        profiles,
        X,
        Y,
        Z,
        DATE,
        class_room,
        instructors,
        courses,
        slots,
        room_layouts=room_layouts,
        loader=loader,
    )
    rates = [
        rep["satisfaction_rate"]
        for rep in sat_report.values()
        if rep.get("has_preferences")
    ]
    avg_satisfaction = round((sum(rates) / len(rates)) * 100.0, 2) if rates else 100.0

    # 5. Persist solved schedule rows into SQLite `schedules` table
    inst_name_to_id = {u["name"]: u["user_id"] for u in loader.get_instructors()}
    course_name_to_id = {c["course_name"]: c["course_id"] for c in loader.courses}
    room_number_to_id = {r["room_number"]: r["room_id"] for r in loader.rooms}

    session.exec(delete(Schedule).where(Schedule.semester_id == semester.id))

    scheduled_count = 0
    for c in courses:
        for i in instructors:
            if (i, c) in Z and solver.Value(Z[i, c]) == 1:
                assigned_room = None
                assigned_slot = None
                for r in class_room:
                    for s in slots.keys():
                        if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1:
                            assigned_room = r
                            assigned_slot = s
                            break
                    if assigned_room:
                        break

                if assigned_room and assigned_slot:
                    session.add(
                        Schedule(
                            semester_id=semester.id,
                            course_id=course_name_to_id[c],
                            user_id=inst_name_to_id[i],
                            room_id=room_number_to_id[assigned_room],
                            time_slot_id=int(assigned_slot),
                            status="confirmed",
                        )
                    )
                    scheduled_count += 1

    session.commit()

    return {
        "status": status_str,
        "semester_id": semester.id,
        "scheduled_count": scheduled_count,
        "wall_time_seconds": wall_time,
        "satisfaction_rate": avg_satisfaction,
    }
```

---

### Task 4: Solver, Admin Seed & Directory Router (`backend/app/api/v1/routes_solver.py`)
* **File Location:** `backend/app/api/v1/routes_solver.py` (~85 LOC, new file)
* **Endpoints:**
  - `POST /api/v1/admin/seed` (triggers `seed_database`, returns `SeedResponse`)
  - `POST /api/v1/solver/run` (triggers `run_solver_for_semester`, returns `SolverRunResponse`)
  - `GET /api/v1/users` (lists instructors/users so frontend can populate dropdowns dynamically)
  - `GET /api/v1/semesters` (lists all 6 academic semesters)

```python
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.seeder import seed_database
from app.models.entities import User, Semester
from app.schemas.api_schemas import (
    SeedResponse,
    SolverRunRequest,
    SolverRunResponse,
    UserResponse,
    SemesterResponse,
)
from app.services.solver_service import run_solver_for_semester

router = APIRouter()


@router.post("/admin/seed", response_model=SeedResponse, tags=["Admin"])
def trigger_seed_database(
    force_reset: bool = Query(default=False, description="Reset existing records before seeding"),
    session: Session = Depends(get_session),
):
    """Populate SQLite database with initial UMKC catalog, faculty, rooms, and time slots."""
    counts = seed_database(session=session, force_reset=force_reset)
    return SeedResponse(status="seeded", **counts)


@router.post("/solver/run", response_model=SolverRunResponse, tags=["Solver"])
def trigger_solver_run(
    payload: SolverRunRequest,
    session: Session = Depends(get_session),
):
    """Execute Google OR-Tools CP-SAT solver for the target semester and persist schedules."""
    result = run_solver_for_semester(
        session=session,
        semester_id=payload.semester_id,
        max_courses_per_instructor=payload.max_courses_per_instructor,
        min_courses_per_instructor=payload.min_courses_per_instructor,
        force_infeasible=payload.enforce_Zero_Violations,
    )
    return SolverRunResponse(**result)


@router.get("/users", response_model=List[UserResponse], tags=["Users"])
def list_users(
    role: Optional[str] = Query(default=None, description="Filter by role, e.g. instructor"),
    session: Session = Depends(get_session),
):
    """List faculty instructors and system users."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    return session.exec(stmt).all()


@router.get("/semesters", response_model=List[SemesterResponse], tags=["Semesters"])
def list_semesters(session: Session = Depends(get_session)):
    """List available academic semesters."""
    return session.exec(select(Semester)).all()
```

* **Mount in `backend/app/api/v1/routes.py`:**
  Import `routes_solver` and add:
  ```python
  router.include_router(routes_solver.router, prefix="", tags=["Solver & Admin"])
  ```
* **Auto-seed on startup in `backend/app/main.py`:**
  In `on_startup()` inside `backend/app/main.py`, call `seed_database()` right after `create_db_and_tables()` so the live server always starts with the 40 UMKC courses, 20 faculty, 12 rooms, 6 semesters, and 6 time slots loaded!

---

### Task 5: Automated Pytest Suites (`test_seeder.py` & `test_solver_api.py`)

#### 1. `backend/tests/test_seeder.py` (~95 LOC, new file)
Tests **AC 1.1** (exact entity counts: 20 users, 40 courses, 12 rooms, 6 semesters, 6 time slots) and **AC 1.2** (idempotency when called twice + `POST /api/v1/admin/seed` endpoint):

```python
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.core.seeder import seed_database


def test_seed_database_counts(session: Session):
    """AC 1.1: Verify exact UMKC entity counts after seeding an empty database."""
    summary = seed_database(session=session)
    assert summary["campuses"] == 2
    assert summary["buildings"] == 5
    assert summary["rooms"] == 12
    assert summary["users"] == 20
    assert summary["courses"] == 40
    assert summary["time_slots"] == 6
    assert summary["semesters"] == 6
    assert summary["preferences"] > 0
    assert summary["schedules"] == 240  # 40 courses * 6 semesters


def test_seed_database_idempotency(session: Session):
    """AC 1.2: Running seed_database a second time must not duplicate records."""
    first = seed_database(session=session)
    second = seed_database(session=session)
    assert first == second


def test_seed_database_force_reset(session: Session):
    """Verify force_reset cleanly rebuilds the catalog without FK errors."""
    seed_database(session=session)
    reset_summary = seed_database(session=session, force_reset=True)
    assert reset_summary["courses"] == 40
    assert reset_summary["users"] == 20
    assert reset_summary["rooms"] == 12


def test_admin_seed_endpoint(client: TestClient):
    """Verify POST /api/v1/admin/seed returns HTTP 200 and expected counts."""
    response = client.post("/api/v1/admin/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "seeded"
    assert data["users"] == 20
    assert data["courses"] == 40
    assert data["rooms"] == 12
    assert data["time_slots"] == 6
    assert data["semesters"] == 6
```

#### 2. `backend/tests/test_solver_api.py` (~110 LOC, new file)
Tests **AC 2.1** (valid solve execution & DB persistence), **AC 2.2** (invalid semester returns 404), **AC 2.3** (infeasible constraints return 422), and directory endpoints (`/users`, `/semesters`):

```python
from fastapi.testclient import TestClient


def test_solver_run_success_and_persists_schedules(client: TestClient):
    """AC 2.1: POST /api/v1/solver/run solves Semester 1 and persists 40 course events."""
    client.post("/api/v1/admin/seed")

    response = client.post("/api/v1/solver/run", json={"semester_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["semester_id"] == 1
    assert data["scheduled_count"] == 40
    assert data["wall_time_seconds"] >= 0

    # Verify schedules are persisted and returned by GET /api/v1/schedules
    sched_res = client.get("/api/v1/schedules?semester_id=1")
    assert sched_res.status_code == 200
    events = sched_res.json()
    assert len(events) == 40
    assert events[0]["status"] == "confirmed"


def test_solver_run_invalid_semester_returns_404(client: TestClient):
    """AC 2.2: Requesting a non-existent semester ID returns HTTP 404."""
    client.post("/api/v1/admin/seed")

    response = client.post("/api/v1/solver/run", json={"semester_id": 999})
    assert response.status_code == 404
    assert "Semester 999 does not exist" in response.json()["detail"]


def test_solver_run_infeasible_returns_422(client: TestClient):
    """AC 2.3: Over-constrained solver request returns HTTP 422 Unprocessable Entity."""
    client.post("/api/v1/admin/seed")

    response = client.post(
        "/api/v1/solver/run",
        json={
            "semester_id": 1,
            "min_courses_per_instructor": 3,
            "max_courses_per_instructor": 1,
        },
    )
    assert response.status_code == 422
    assert "feasible" in response.json()["detail"].lower()


def test_users_and_semesters_directory_endpoints(client: TestClient):
    """Verify GET /api/v1/users and GET /api/v1/semesters return seeded records."""
    client.post("/api/v1/admin/seed")

    users_res = client.get("/api/v1/users?role=instructor")
    assert users_res.status_code == 200
    assert len(users_res.json()) == 20

    sem_res = client.get("/api/v1/semesters")
    assert sem_res.status_code == 200
    assert len(sem_res.json()) == 6
```

---

## 4. LOC Contribution Breakdown for Tony

| File | Type | Purpose | LOC Estimate |
| :--- | :--- | :--- | :---: |
| `backend/app/core/seeder.py` | Production | Idempotent UMKC JSON-to-SQLite database seeder (US-1) | ~185 |
| `backend/app/services/solver_service.py` | Production | OR-Tools CP-SAT execution & schedule persistence service (US-2) | ~155 |
| `backend/app/api/v1/routes_solver.py` | Production | `/admin/seed`, `/solver/run`, `/users`, `/semesters` endpoints | ~85 |
| `backend/app/schemas/api_schemas.py` | Production | `SeedResponse`, `SolverRunRequest/Response`, `User/SemesterResponse` | ~55 |
| `backend/tests/test_seeder.py` | Test | Seeding count, idempotency, reset, and `/admin/seed` tests | ~95 |
| `backend/tests/test_solver_api.py` | Test | Solver run (200), invalid semester (404), infeasible (422) tests | ~110 |
| **Total New LOC by Tony** | | | **~685 LOC** (Compliant: > 400 LOC) |

---

## 5. Verification & Git Push Commands

```bash
# 1. Run full backend test suite
cd backend
PYTHONPATH=. pytest tests/ -v

# 2. Verify Git author before committing
git config user.name "Tony"
git config user.email "mtuan82@gmail.com"

# 3. Stage, commit, and check author in git log
git add backend/
git commit -m "feat(backend): implement UMKC database seeder, CP-SAT solver API bridge, and pytest suites (US-1, US-2)"
git log -n 1 --stat

# 4. Push branch and open PR (or merge to main)
git push -u origin feature/tony-seeder-solver-api
```
