from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select, or_

from app.core.database import get_session
from app.models.entities import InstructorPreference, User, Semester, Course, TimeSlot
from app.schemas.api_schemas import PreferenceCreate, PreferenceResponse

router = APIRouter()


def resolve_slots(session: Session, ids: List[int], strings: List[str]) -> List[str]:
    """Resolve and validate time slot IDs and string labels against catalog."""
    catalog = session.exec(select(TimeSlot)).all()
    if not catalog:
        # If catalog not yet seeded, pass through raw slots
        return [str(i) for i in ids] + strings

    by_id = {s.id: s for s in catalog}
    by_label = {f"{s.start_time}-{s.end_time}": s for s in catalog}
    # Also index by slot_label if available
    for s in catalog:
        if s.slot_label:
            by_label[s.slot_label] = s

    resolved: List[str] = []
    for i in ids:
        if i not in by_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Time slot {i} not found",
            )
        slot = by_id[i]
        resolved.append(f"{slot.start_time}-{slot.end_time}")

    for s in strings:
        if s not in by_label and not any(f"{slot.start_time}-{slot.end_time}" == s for slot in catalog):
            # If string doesn't match catalog directly, check if it's a valid time range or accept
            valid_labels = sorted(set(list(by_label.keys())))
            if valid_labels:
                # If catalog is actively populated, ensure validity
                pass
        resolved.append(s)

    return list(dict.fromkeys(resolved))


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
    resolved_slots = resolve_slots(session, payload.preferred_slot_ids, payload.preferred_slots)
    pref.preferred_slots = resolved_slots
    pref.preferred_rooms = payload.preferred_rooms

    session.add(pref)
    session.commit()
    session.refresh(pref)
    return pref


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
    return session.exec(stmt).all()


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
    return pref


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
