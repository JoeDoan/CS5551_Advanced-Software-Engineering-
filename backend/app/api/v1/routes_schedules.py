from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import SessionPrincipal, require_coordinator
from app.models.entities import Schedule
from app.schemas.api_schemas import (
    MultiSemesterSimulationRequest,
    MultiSemesterSimulationResponse,
    ScheduleCreateRequest,
    ScheduleEventResponse,
    ScheduleOverrideRequest,
)
from app.services.simulation_service import (
    build_schedule_event_response,
    create_schedule_assignment,
    delete_schedule_assignment,
    override_schedule_assignment,
    run_multi_semester_simulation,
)

router = APIRouter()


@router.post(
    "/solver/simulate",
    response_model=MultiSemesterSimulationResponse,
    tags=["Solver"],
)
def simulate_multi_semester_schedules(
    payload: MultiSemesterSimulationRequest,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Run sequential multi-semester CP-SAT simulation with priority carryover."""
    return run_multi_semester_simulation(
        session=session,
        semester_ids=payload.semester_ids,
        max_courses_per_instructor=payload.max_courses_per_instructor,
        min_courses_per_instructor=payload.min_courses_per_instructor,
        reset_priorities_before_run=payload.reset_priorities_before_run,
    )


@router.post(
    "/schedules",
    response_model=ScheduleEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Schedules"],
)
def create_schedule_section(
    payload: ScheduleCreateRequest,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Manually schedule a new course section after constraint validation."""
    return create_schedule_assignment(session=session, payload=payload)


@router.get(
    "/schedules/{schedule_id}",
    response_model=ScheduleEventResponse,
    tags=["Schedules"],
)
def get_schedule_by_id(
    schedule_id: int,
    session: Session = Depends(get_session),
):
    """Retrieve a single scheduled course assignment by ID."""
    sched = session.get(Schedule, schedule_id)
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )
    return build_schedule_event_response(session, sched)


@router.patch(
    "/schedules/{schedule_id}",
    response_model=ScheduleEventResponse,
    tags=["Schedules"],
)
def patch_schedule_assignment(
    schedule_id: int,
    payload: ScheduleOverrideRequest,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Manually override room, time slot, instructor, or status on a schedule row."""
    return override_schedule_assignment(
        session=session,
        schedule_id=schedule_id,
        payload=payload,
    )


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Schedules"],
)
def delete_schedule_section(
    schedule_id: int,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Unschedule a course section and remove dependent edit requests."""
    delete_schedule_assignment(session=session, schedule_id=schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
