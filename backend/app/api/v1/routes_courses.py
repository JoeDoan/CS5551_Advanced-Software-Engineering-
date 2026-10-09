from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select, or_
from sqlalchemy.exc import IntegrityError

from app.core.database import get_session
from app.models.entities import Course, Schedule, InstructorPreference
from app.schemas.api_schemas import CourseCreate, CourseUpdate, CourseResponse

router = APIRouter()


@router.get("", response_model=List[CourseResponse])
def list_courses(
    department: Optional[str] = Query(default=None, description="Filter by department"),
    search: Optional[str] = Query(default=None, description="Search course code or name"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """Retrieve catalog courses with optional filtering, search, and pagination."""
    stmt = select(Course)
    if department:
        stmt = stmt.where(Course.department == department.upper())
    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            or_(Course.course_code.ilike(term), Course.course_name.ilike(term))
        )
    return session.exec(stmt.offset(offset).limit(limit)).all()


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    session: Session = Depends(get_session),
):
    """Add a new course to the catalog with duplicate code detection."""
    existing = session.exec(
        select(Course).where(Course.course_code == payload.course_code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with code '{payload.course_code}' already exists",
        )

    course = Course(**payload.model_dump())
    try:
        session.add(course)
        session.commit()
        session.refresh(course)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course with this code already exists",
        )
    return course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    session: Session = Depends(get_session),
):
    """Retrieve a single course by its unique ID."""
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    session: Session = Depends(get_session),
):
    """Update course attributes."""
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if payload.course_code and payload.course_code != course.course_code:
        duplicate = session.exec(
            select(Course).where(Course.course_code == payload.course_code)
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Course with code '{payload.course_code}' already exists",
            )
        course.course_code = payload.course_code

    if payload.course_name is not None:
        course.course_name = payload.course_name
    if payload.department is not None:
        course.department = payload.department
    if payload.credits is not None:
        course.credits = payload.credits
    if payload.expected_enrollment is not None:
        course.expected_enrollment = payload.expected_enrollment
    if payload.requires_lab is not None:
        course.requires_lab = payload.requires_lab

    try:
        session.add(course)
        session.commit()
        session.refresh(course)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database integrity error updating course",
        )
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    session: Session = Depends(get_session),
):
    """Delete a course with foreign key dependency protection."""
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Delete guard: check if used in active schedule or instructor preference
    used_sched = session.exec(
        select(Schedule.id).where(Schedule.course_id == course_id)
    ).first()
    used_pref = session.exec(
        select(InstructorPreference.id).where(InstructorPreference.course_id == course_id)
    ).first()
    if used_sched or used_pref:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course is used by a schedule or preference",
        )

    session.delete(course)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
