import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select, or_

from app.core.database import get_session
from app.models.entities import InstructorPreference, User, Semester, Course, TimeSlot
from app.schemas.api_schemas import PreferenceCreate, PreferenceResponse

router = APIRouter()


def course_level(course_code: str) -> str:
    """Course numbers 5000+ are graduate-level (derived from the course code)."""
    m = re.search(r"\d+", course_code)
    return "graduate" if m and int(m.group()) >= 5000 else "undergraduate"


def _label(slot: TimeSlot) -> str:
    return f"{slot.start_time}-{slot.end_time}"


def resolve_slots(
    session: Session,
    ids: List[int],
    strings: List[str],
    course: Optional[Course] = None,
) -> List[str]:
    """Resolve slot ids/labels against the catalog and return canonical 'HH:MM-HH:MM' labels."""
    catalog = session.exec(select(TimeSlot)).all()
    if not catalog:
        # Catalog not yet seeded: pass raw values through.
        return list(dict.fromkeys([str(i) for i in ids] + strings))

    by_id = {s.id: s for s in catalog}
    by_label = {_label(s): s for s in catalog}
    for s in catalog:
        if s.slot_label:
            by_label.setdefault(s.slot_label, s)

    slots: List[TimeSlot] = []
    for i in ids:
        if i not in by_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Time slot {i} not found",
            )
        slots.append(by_id[i])
    for s in strings:
        if s not in by_label:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown slot {s}. Valid: {sorted({_label(c) for c in catalog})}",
            )
        slots.append(by_label[s])

    if course is not None:
        level = course_level(course.course_code)
        for s in slots:
            if s.level and s.level != level:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Slot {_label(s)} is {s.level}-only",
                )
    return list(dict.fromkeys(_label(s) for s in slots))


def to_response(session: Session, pref: InstructorPreference) -> PreferenceResponse:
    """Build the response, adding catalog slot ids for the stored labels (AC 5.14)."""
    labels = pref.preferred_slots if isinstance(pref.preferred_slots, list) else []
    by_label = {_label(s): s.id for s in session.exec(select(TimeSlot)).all()}
    return PreferenceResponse(
        id=pref.id,
        user_id=pref.user_id,
        semester_id=pref.semester_id,
        course_id=pref.course_id,
        preferred_days=pref.preferred_days,
        preferred_slots=pref.preferred_slots,
        preferred_slot_ids=[by_label[l] for l in labels if l in by_label],
        preferred_rooms=pref.preferred_rooms,
        preference_rank=pref.preference_rank,
    )


@router.post("", response_model=PreferenceResponse)
def submit_preference(
    payload: PreferenceCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    """Submit instructor availability and course preferences with idempotent upsert."""
    # 1. Validate User
    user = session.get(User, payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can submit preferences",
        )

    # 2. Validate Semester
    sem = session.get(Semester, payload.semester_id)
    if not sem:
        sem = session.exec(
            select(Semester).where(Semester.semester_id == payload.semester_id)
        ).first()
    if not sem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found",
        )

    # 3. Validate Course if provided
    course = None
    if payload.course_id is not None:
        course = session.get(Course, payload.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

    # 4. Upsert check (AC 5.3: resubmission replaces existing record)
    course_match = (
        InstructorPreference.course_id == payload.course_id
        if payload.course_id is not None
        else InstructorPreference.course_id.is_(None)
    )
    pref = session.exec(
        select(InstructorPreference).where(
            InstructorPreference.user_id == payload.user_id,
            InstructorPreference.semester_id == payload.semester_id,
            course_match,
        )
    ).first()

    if pref is None:
        pref = InstructorPreference(
            user_id=payload.user_id,
            semester_id=payload.semester_id,
            course_id=payload.course_id,
        )
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    # 5. Populate and resolve preferences
    pref.preferred_days = payload.preferred_days
    resolved_slots = resolve_slots(session, payload.preferred_slot_ids, payload.preferred_slots, course)
    pref.preferred_slots = resolved_slots
    pref.preferred_rooms = payload.preferred_rooms

    session.add(pref)
    session.commit()
    session.refresh(pref)
    return to_response(session, pref)


@router.get("", response_model=List[PreferenceResponse])
def get_preferences(
    user_id: Optional[int] = Query(default=None, description="Filter by instructor ID (optional for coordinator)"),
    semester_id: Optional[int] = Query(default=None, description="Filter by semester ID"),
    course_id: Optional[int] = Query(default=None, description="Filter by course ID"),
    session: Session = Depends(get_session),
):
    """Retrieve instructor preferences with optional filtering by instructor, semester, or course."""
    stmt = select(InstructorPreference)
    if user_id is not None:
        stmt = stmt.where(InstructorPreference.user_id == user_id)
    if semester_id is not None:
        stmt = stmt.where(InstructorPreference.semester_id == semester_id)
    if course_id is not None:
        stmt = stmt.where(InstructorPreference.course_id == course_id)
    return [to_response(session, p) for p in session.exec(stmt).all()]


@router.get("/{preference_id}", response_model=PreferenceResponse)
def get_preference(
    preference_id: int,
    session: Session = Depends(get_session),
):
    """Retrieve a single preference record."""
    pref = session.get(InstructorPreference, preference_id)
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found",
        )
    return to_response(session, pref)


@router.delete("/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preference(
    preference_id: int,
    session: Session = Depends(get_session),
):
    """Delete an instructor preference record."""
    pref = session.get(InstructorPreference, preference_id)
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found",
        )
    session.delete(pref)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
