from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import SessionPrincipal, require_coordinator
from app.core.seeder import seed_database
from app.models.entities import User
from app.schemas.api_schemas import (
    SeedResponse,
    SolverRunRequest,
    SolverRunResponse,
    UserResponse,
)
from app.services.solver_service import run_solver_for_semester

router = APIRouter()


@router.post("/admin/seed", response_model=SeedResponse, tags=["Admin"])
def trigger_seed_database(
    force_reset: bool = Query(
        default=False, description="Reset existing records before seeding"
    ),
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Populate SQLite with the UMKC catalog, faculty, rooms, and time slots (idempotent)."""
    counts = seed_database(session=session, force_reset=force_reset)
    return SeedResponse(status="seeded", **counts)


@router.post("/solver/run", response_model=SolverRunResponse, tags=["Solver"])
def trigger_solver_run(
    payload: SolverRunRequest,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
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


@router.get("/instructors", response_model=List[UserResponse], tags=["Users"])
def list_instructors(
    department: Optional[str] = Query(
        default=None, description="Filter instructors by department"
    ),
    session: Session = Depends(get_session),
):
    """List all instructor profiles from the users catalog."""
    stmt = select(User).where(User.role == "instructor")
    if department:
        stmt = stmt.where(User.department == department.strip().upper())
    return session.exec(stmt.order_by(User.id)).all()
