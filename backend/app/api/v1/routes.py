from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.schemas.api_schemas import (
    HealthResponse,
    CourseResponse,
    RoomResponse,
    PreferenceCreate,
    PreferenceResponse,
    ScheduleEventResponse,
)
from app.models.entities import Course, Room, InstructorPreference, Schedule

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/courses", response_model=List[CourseResponse], tags=["Courses"])
def list_courses(
    department: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Retrieve catalog courses, optionally filtered by department."""
    statement = select(Course)
    if department:
        statement = statement.where(Course.department == department)
    courses = session.exec(statement).all()
    return courses


@router.get("/rooms", response_model=List[RoomResponse], tags=["Rooms"])
def list_rooms(
    min_capacity: Optional[int] = None,
    session: Session = Depends(get_session),
):
    """Retrieve classrooms and laboratories."""
    statement = select(Room)
    if min_capacity is not None:
        statement = statement.where(Room.capacity >= min_capacity)
    rooms = session.exec(statement).all()
    return rooms


@router.post("/preferences", response_model=PreferenceResponse, status_code=201, tags=["Preferences"])
def submit_preference(
    payload: PreferenceCreate,
    session: Session = Depends(get_session),
):
    """Submit or update instructor teaching preferences."""
    pref = InstructorPreference(
        user_id=payload.user_id,
        semester_id=payload.semester_id,
        course_id=payload.course_id,
        preferred_days=",".join(payload.preferred_days) if payload.preferred_days else None,
        preferred_slots=",".join(payload.preferred_slots) if payload.preferred_slots else None,
        preferred_rooms=",".join(payload.preferred_rooms) if payload.preferred_rooms else None,
        preference_rank=1,
    )
    session.add(pref)
    session.commit()
    session.refresh(pref)
    return pref


@router.get("/schedules", response_model=List[ScheduleEventResponse], tags=["Schedules"])
def get_schedule(
    semester_id: int = Query(default=1, description="Semester ID (1=Fall 2024 .. 6=Spring 2027)"),
    session: Session = Depends(get_session),
):
    """Retrieve the generated schedule for a given semester."""
    # Stubs: Return empty list if no schedules found in DB yet
    return []
