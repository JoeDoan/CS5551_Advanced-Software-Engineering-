from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.api.v1.routes_preferences import course_level
from app.core.database import get_session
from app.core.security import SessionPrincipal, require_coordinator
from app.models.entities import Course, InstructorCourseAssignment, Semester, User
from app.schemas.api_schemas import (
    CourseAssignmentBulkPut,
    CourseAssignmentCreate,
    CourseAssignmentResponse,
)

router = APIRouter()


def _resolve_semester(session: Session, semester_id: int) -> Semester:
    sem = session.get(Semester, semester_id)
    if sem is None:
        sem = session.exec(
            select(Semester).where(Semester.semester_id == semester_id)
        ).first()
    if sem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester {semester_id} not found",
        )
    return sem


def _resolve_instructor(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    if user.role != "instructor":
        raise HTTPException(
            status_code=422,
            detail="Courses can only be assigned to users with the instructor role.",
        )
    return user


def _to_response(
    assignment: InstructorCourseAssignment,
    user: User,
    course: Course,
) -> CourseAssignmentResponse:
    return CourseAssignmentResponse(
        id=assignment.id,
        semester_id=assignment.semester_id,
        user_id=assignment.user_id,
        instructor_name=user.full_name,
        instructor_department=user.department,
        course_id=assignment.course_id,
        course_code=course.course_code,
        course_name=course.course_name,
        department=course.department,
        course_level=course_level(course.course_code),
    )


@router.get("", response_model=List[CourseAssignmentResponse])
def list_course_assignments(
    semester_id: Optional[int] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    department: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = (
        select(InstructorCourseAssignment, User, Course)
        .join(User, User.id == InstructorCourseAssignment.user_id)
        .join(Course, Course.id == InstructorCourseAssignment.course_id)
    )
    if semester_id is not None:
        sem = session.get(Semester, semester_id) or session.exec(
            select(Semester).where(Semester.semester_id == semester_id)
        ).first()
        target_sem_id = sem.id if sem is not None else semester_id
        stmt = stmt.where(InstructorCourseAssignment.semester_id == target_sem_id)
    if user_id is not None:
        stmt = stmt.where(InstructorCourseAssignment.user_id == user_id)
    if department is not None and department.strip():
        stmt = stmt.where(
            func.lower(Course.department) == department.strip().lower()
        )

    stmt = stmt.order_by(
        InstructorCourseAssignment.semester_id,
        InstructorCourseAssignment.user_id,
        Course.course_code,
    )
    rows = session.exec(stmt).all()
    items = [
        _to_response(assignment, user, course) for assignment, user, course in rows
    ]
    if level is not None and level.strip():
        target_level = level.strip().lower()
        items = [item for item in items if item.course_level == target_level]
    return items


@router.put("", response_model=List[CourseAssignmentResponse])
def replace_course_assignments(
    payload: CourseAssignmentBulkPut,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    sem = _resolve_semester(session, payload.semester_id)
    user = _resolve_instructor(session, payload.user_id)
    dedup_course_ids = list(dict.fromkeys(payload.course_ids))

    courses_by_id: Dict[int, Course] = {}
    for cid in dedup_course_ids:
        course = session.get(Course, cid)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course {cid} not found",
            )
        courses_by_id[cid] = course

    session.execute(
        delete(InstructorCourseAssignment).where(
            InstructorCourseAssignment.semester_id == sem.id,
            InstructorCourseAssignment.user_id == user.id,
        )
    )
    session.flush()

    for cid in dedup_course_ids:
        session.add(
            InstructorCourseAssignment(
                semester_id=sem.id,
                user_id=user.id,
                course_id=cid,
            )
        )
    session.commit()

    rows = session.exec(
        select(InstructorCourseAssignment, Course)
        .join(Course, Course.id == InstructorCourseAssignment.course_id)
        .where(
            InstructorCourseAssignment.semester_id == sem.id,
            InstructorCourseAssignment.user_id == user.id,
        )
        .order_by(Course.course_code)
    ).all()
    return [_to_response(assignment, user, course) for assignment, course in rows]


@router.post("", response_model=CourseAssignmentResponse)
def create_course_assignment(
    payload: CourseAssignmentCreate,
    response: Response,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    sem = _resolve_semester(session, payload.semester_id)
    user = _resolve_instructor(session, payload.user_id)
    course = session.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {payload.course_id} not found",
        )

    existing = session.exec(
        select(InstructorCourseAssignment).where(
            InstructorCourseAssignment.semester_id == sem.id,
            InstructorCourseAssignment.user_id == user.id,
            InstructorCourseAssignment.course_id == course.id,
        )
    ).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _to_response(existing, user, course)

    assignment = InstructorCourseAssignment(
        semester_id=sem.id,
        user_id=user.id,
        course_id=course.id,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    response.status_code = status.HTTP_201_CREATED
    return _to_response(assignment, user, course)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_assignment(
    assignment_id: int,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    assignment = session.get(InstructorCourseAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course assignment not found",
        )
    session.delete(assignment)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
