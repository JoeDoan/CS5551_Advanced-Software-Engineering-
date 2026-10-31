from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_session
from app.schemas.api_schemas import (
    HealthResponse,
    ScheduleEventResponse,
    SemesterResponse,
)
from app.models.entities import Schedule, Course, User, Room, TimeSlot, Semester
from app.api.v1 import (
    routes_analytics,
    routes_assignments,
    routes_auth,
    routes_courses,
    routes_edit_requests,
    routes_export,
    routes_forecast,
    routes_rooms,
    routes_preferences,
    routes_scenarios,
    routes_schedules,
    routes_time_slots,
    routes_solver,
)

router = APIRouter()

# Mount dedicated CRUD and Catalog routers
router.include_router(
    routes_auth.router, prefix="/auth", tags=["Authentication"]
)
router.include_router(routes_courses.router, prefix="/courses", tags=["Courses"])
router.include_router(routes_rooms.router, prefix="/rooms", tags=["Rooms"])
router.include_router(
    routes_preferences.router, prefix="/preferences", tags=["Preferences"]
)
router.include_router(
    routes_assignments.router,
    prefix="/course-assignments",
    tags=["Course Assignments"],
)
router.include_router(
    routes_time_slots.router, prefix="/time-slots", tags=["Time Slots"]
)
router.include_router(routes_solver.router, prefix="")
router.include_router(routes_export.router, prefix="")
router.include_router(routes_schedules.router, prefix="")
router.include_router(
    routes_edit_requests.router, prefix="/edit-requests", tags=["Edit Requests"]
)
router.include_router(
    routes_analytics.router, prefix="/analytics", tags=["Analytics"]
)
router.include_router(
    routes_forecast.router, prefix="/forecast", tags=["Forecast"]
)
router.include_router(
    routes_scenarios.router, prefix="/scenarios", tags=["Scenarios"]
)


@router.get("/semesters", response_model=List[SemesterResponse], tags=["Semesters"])
def list_semesters(session: Session = Depends(get_session)):
    """List available academic semesters."""
    return session.exec(select(Semester).order_by(Semester.semester_id)).all()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/schedules", response_model=List[ScheduleEventResponse], tags=["Schedules"]
)
def get_schedule(
    semester_id: int = Query(
        default=1, description="Semester ID (1=Fall 2024 .. 6=Spring 2027)"
    ),
    session: Session = Depends(get_session),
):
    """Retrieve the generated schedule for a given semester."""
    # Query database schedules joined with entities
    results = session.exec(
        select(Schedule, Course, User, Room, TimeSlot)
        .join(Course, Course.id == Schedule.course_id)
        .join(User, User.id == Schedule.user_id)
        .join(Room, Room.id == Schedule.room_id)
        .join(TimeSlot, TimeSlot.id == Schedule.time_slot_id)
        .where(Schedule.semester_id == semester_id)
    ).all()

    if not results:
        return []

    events = []
    for sched, course, user, room, slot in results:
        events.append(
            ScheduleEventResponse(
                id=sched.id,
                semester_id=sched.semester_id,
                course_id=sched.course_id,
                user_id=sched.user_id,
                room_id=sched.room_id,
                time_slot_id=sched.time_slot_id,
                department=course.department,
                course_code=course.course_code,
                course_name=course.course_name,
                instructor_name=user.full_name,
                room_number=room.room_number,
                day_pattern=slot.day_pattern,
                start_time=slot.start_time,
                end_time=slot.end_time,
                status=sched.status,
            )
        )
    return events
