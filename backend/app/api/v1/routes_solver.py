from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.seeder import seed_database
from app.models.entities import Semester, User
from app.schemas.api_schemas import (
    SeedResponse,
    SemesterResponse,
    SolverRunRequest,
    SolverRunResponse,
    UserResponse,
)
from app.services.solver_service import run_solver_for_semester

router = APIRouter()


@router.post("/admin/seed", response_model=SeedResponse, tags=["Admin"])
def trigger_seed_database(
    force_reset: bool = Query(default=False, description="Reset existing records before seeding"),
    session: Session = Depends(get_session),
):
    """Populate SQLite with the UMKC catalog, faculty, rooms, and time slots (idempotent)."""
    counts = seed_database(session=session, force_reset=force_reset)
    return SeedResponse(status="seeded", **counts)


@router.post("/solver/run", response_model=SolverRunResponse, tags=["Solver"])
def trigger_solver_run(
    payload: SolverRunRequest,
    session: Session = Depends(get_session),
):
    """Run the CP-SAT solver for a semester and persist the resulting schedule."""
    result = run_solver_for_semester(
        session=session,
        semester_id=payload.semester_id,
        max_courses_per_instructor=payload.max_courses_per_instructor,
        min_courses_per_instructor=payload.min_courses_per_instructor,
        force_infeasible=payload.enforce_zero_violations,
    )
    return SolverRunResponse(**result)


@router.get("/users", response_model=List[UserResponse], tags=["Users"])
def list_users(
    role: Optional[str] = Query(default=None, description="Filter by role, e.g. instructor"),
    session: Session = Depends(get_session),
):
    """List users so the frontend can populate instructor dropdowns."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    return session.exec(stmt).all()


@router.get("/semesters", response_model=List[SemesterResponse], tags=["Semesters"])
def list_semesters(session: Session = Depends(get_session)):
    """List available academic semesters."""
    return session.exec(select(Semester).order_by(Semester.semester_id)).all()
