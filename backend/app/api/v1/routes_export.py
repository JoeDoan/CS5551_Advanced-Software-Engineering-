from collections import Counter
import csv
from dataclasses import dataclass
import io
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import SessionPrincipal, require_coordinator
from app.core.seeder import seed_database
from app.models.entities import (
    Course,
    EditRequest,
    Room,
    Schedule,
    Semester,
    TimeSlot,
    User,
)

router = APIRouter()

ICS_DAY_MAP: Dict[str, str] = {
    "M": "MO",
    "T": "TU",
    "W": "WE",
    "R": "TH",
    "F": "FR",
}

FIRST_CLASS_DATE_BY_LETTER: Dict[str, str] = {
    "M": "20240826",
    "T": "20240827",
    "W": "20240828",
    "R": "20240829",
    "F": "20240830",
}

CSV_EXPORT_HEADERS: List[str] = [
    "Schedule ID",
    "Semester ID",
    "Course Code",
    "Course Name",
    "Department",
    "Instructor",
    "Room",
    "Day Pattern",
    "Start Time",
    "End Time",
    "Status",
]


@dataclass(frozen=True)
class JoinedScheduleRow:
    schedule: Schedule
    course: Course
    user: User
    room: Room
    slot: TimeSlot


class CloneSemesterRequest(BaseModel):
    source_semester_id: int = Field(..., ge=1, description="Source semester ID")
    target_semester_id: int = Field(..., ge=1, description="Target semester ID")
    overwrite: bool = Field(
        default=True,
        description="If true, replaces existing schedules in target semester",
    )


class CloneSemesterResponse(BaseModel):
    source_semester_id: int
    target_semester_id: int
    cloned_count: int
    status: str = "cloned"


class ScheduleSnapshotSummaryResponse(BaseModel):
    semester_id: int
    semester_name: str
    total_events: int
    unique_instructors: int
    unique_rooms: int
    courses_by_department: Dict[str, int]
    events_by_day_pattern: Dict[str, int]
    events_by_status: Dict[str, int]


def _query_joined_schedules(
    session: Session, semester_id: int, department: Optional[str] = None
) -> Tuple[Semester, List[JoinedScheduleRow]]:
    if session.exec(select(Semester).limit(1)).first() is None:
        seed_database(session=session)

    sem = session.exec(
        select(Semester).where(
            (Semester.id == semester_id) | (Semester.semester_id == semester_id)
        )
    ).first()
    if sem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester {semester_id} not found",
        )

    stmt = (
        select(Schedule, Course, User, Room, TimeSlot)
        .join(Course, Course.id == Schedule.course_id)
        .join(User, User.id == Schedule.user_id)
        .join(Room, Room.id == Schedule.room_id)
        .join(TimeSlot, TimeSlot.id == Schedule.time_slot_id)
        .where(Schedule.semester_id == sem.id)
    )
    rows = [
        JoinedScheduleRow(
            schedule=sched,
            course=course,
            user=user,
            room=room,
            slot=slot,
        )
        for sched, course, user, room, slot in session.exec(stmt).all()
    ]
    if department:
        dept_upper = department.strip().upper()
        rows = [
            row for row in rows if row.course.department.upper() == dept_upper
        ]
    return sem, rows


@router.get(
    "/export/summary",
    response_model=ScheduleSnapshotSummaryResponse,
    tags=["Export"],
)
def get_schedule_export_summary(
    semester_id: int = Query(default=1, description="Semester ID to summarize"),
    department: Optional[str] = Query(
        default=None, description="Optional department filter"
    ),
    session: Session = Depends(get_session),
):
    """Return breakdown of scheduled courses by department, day pattern, and status."""
    sem, rows = _query_joined_schedules(session, semester_id, department)

    dept_counter: Counter = Counter()
    day_counter: Counter = Counter()
    status_counter: Counter = Counter()
    instructor_ids = set()
    room_ids = set()

    for row in rows:
        dept_counter[row.course.department] += 1
        day_counter[row.slot.day_pattern] += 1
        status_counter[row.schedule.status] += 1
        instructor_ids.add(row.user.id)
        room_ids.add(row.room.id)

    return ScheduleSnapshotSummaryResponse(
        semester_id=sem.id,
        semester_name=sem.name,
        total_events=len(rows),
        unique_instructors=len(instructor_ids),
        unique_rooms=len(room_ids),
        courses_by_department=dict(dept_counter),
        events_by_day_pattern=dict(day_counter),
        events_by_status=dict(status_counter),
    )


@router.get("/export/schedules.csv", tags=["Export"])
def export_schedules_csv(
    semester_id: int = Query(default=1, description="Semester ID to export"),
    department: Optional[str] = Query(
        default=None, description="Optional department filter (e.g. CS)"
    ),
    session: Session = Depends(get_session),
):
    """Stream semester schedule assignments as an RFC 4180 CSV attachment."""
    sem, rows = _query_joined_schedules(session, semester_id, department)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_EXPORT_HEADERS)
    for row in rows:
        writer.writerow(
            [
                row.schedule.id,
                row.schedule.semester_id,
                row.course.course_code,
                row.course.course_name,
                row.course.department,
                row.user.full_name,
                row.room.room_number,
                row.slot.day_pattern,
                row.slot.start_time,
                row.slot.end_time,
                row.schedule.status,
            ]
        )

    filename = f"schedule_semester_{sem.id}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _format_ics_time(date_str: str, hhmm: str) -> str:
    parts = hhmm.strip().split(":")
    hh = parts[0].zfill(2)
    mm = parts[1].zfill(2) if len(parts) > 1 else "00"
    return f"{date_str}T{hh}{mm}00"


@router.get("/export/schedules.ics", tags=["Export"])
def export_schedules_ics(
    semester_id: int = Query(default=1, description="Semester ID to export"),
    department: Optional[str] = Query(
        default=None, description="Optional department filter"
    ),
    session: Session = Depends(get_session),
):
    """Generate an RFC 5545 iCalendar (.ics) feed for calendar clients."""
    sem, rows = _query_joined_schedules(session, semester_id, department)

    lines: List[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UMKC OptiSched//Course Timetable Scheduler//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for row in rows:
        pattern = (row.slot.day_pattern or "M").strip().upper()
        byday_tokens = [
            ICS_DAY_MAP[ch] for ch in pattern if ch in ICS_DAY_MAP
        ]
        byday_str = ",".join(byday_tokens) if byday_tokens else "MO"
        first_letter = (
            pattern[0]
            if pattern and pattern[0] in FIRST_CLASS_DATE_BY_LETTER
            else "M"
        )
        base_date = FIRST_CLASS_DATE_BY_LETTER[first_letter]

        dtstart = _format_ics_time(base_date, row.slot.start_time)
        dtend = _format_ics_time(base_date, row.slot.end_time)

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:optisched-{sem.id}-{row.schedule.id}@umkc.edu",
                f"SUMMARY:{row.course.course_code} - {row.course.course_name}",
                (
                    f"DESCRIPTION:Instructor: {row.user.full_name} "
                    f"| Status: {row.schedule.status}"
                ),
                f"LOCATION:{row.room.room_number}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"RRULE:FREQ=WEEKLY;BYDAY={byday_str};COUNT=16",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    ics_payload = "\r\n".join(lines) + "\r\n"
    filename = f"schedule_semester_{sem.id}.ics"

    return Response(
        content=ics_payload,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/schedules/clone-semester",
    response_model=CloneSemesterResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Schedules"],
)
def clone_semester_schedules(
    payload: CloneSemesterRequest,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Clone all schedule rows from source_semester_id into target_semester_id."""
    if payload.source_semester_id == payload.target_semester_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_semester_id and target_semester_id must be different",
        )

    src_sem = session.exec(
        select(Semester).where(
            (Semester.id == payload.source_semester_id)
            | (Semester.semester_id == payload.source_semester_id)
        )
    ).first()
    if not src_sem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source semester {payload.source_semester_id} not found",
        )

    tgt_sem = session.exec(
        select(Semester).where(
            (Semester.id == payload.target_semester_id)
            | (Semester.semester_id == payload.target_semester_id)
        )
    ).first()
    if not tgt_sem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target semester {payload.target_semester_id} not found",
        )

    existing_target = session.exec(
        select(Schedule).where(Schedule.semester_id == tgt_sem.id)
    ).all()
    if existing_target and not payload.overwrite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Target semester {tgt_sem.id} already has "
                f"{len(existing_target)} scheduled events and overwrite is False"
            ),
        )

    if existing_target and payload.overwrite:
        target_sched_ids = [row.id for row in existing_target if row.id is not None]
        if target_sched_ids:
            session.execute(
                delete(EditRequest).where(EditRequest.schedule_id.in_(target_sched_ids))
            )
        session.execute(
            delete(Schedule).where(Schedule.semester_id == tgt_sem.id)
        )

    source_rows = session.exec(
        select(Schedule).where(Schedule.semester_id == src_sem.id)
    ).all()

    cloned_count = 0
    for row in source_rows:
        session.add(
            Schedule(
                semester_id=tgt_sem.id,
                course_id=row.course_id,
                user_id=row.user_id,
                room_id=row.room_id,
                time_slot_id=row.time_slot_id,
                status="confirmed",
            )
        )
        cloned_count += 1

    session.commit()
    return CloneSemesterResponse(
        source_semester_id=src_sem.id,
        target_semester_id=tgt_sem.id,
        cloned_count=cloned_count,
        status="cloned",
    )
