from dataclasses import dataclass
from typing import List, Optional

from fastapi import HTTPException, status
from ortools.sat.python import cp_model
from sqlalchemy import delete
from sqlmodel import Session, select

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
from app.schemas.api_schemas import (
    InstructorPriorityDelta,
    MultiSemesterSimulationResponse,
    ScheduleCreateRequest,
    ScheduleEventResponse,
    ScheduleOverrideRequest,
    SemesterSimulationResult,
)
from app.solver.data_loader import DataLoader
from app.solver.engine import (
    BASE_PRIORITY,
    DATE,
    build_schedule_model,
    evaluate_satisfaction_and_update,
    get_metadata,
    load_profiles_from_data,
)

SOLVER_TIME_LIMIT_SECONDS = 30.0


@dataclass(frozen=True)
class ResolvedOverrideTarget:
    schedule: Schedule
    course: Course
    room: Room
    slot: TimeSlot
    user: User


def build_schedule_event_response(
    session: Session, sched: Schedule
) -> ScheduleEventResponse:
    """Hydrate a Schedule row with joined Course, User, Room, and TimeSlot fields."""
    course = session.get(Course, sched.course_id)
    user = session.get(User, sched.user_id)
    room = session.get(Room, sched.room_id)
    slot = session.get(TimeSlot, sched.time_slot_id)
    if not (course and user and room and slot):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {sched.id} has missing foreign key references",
        )
    return ScheduleEventResponse(
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


def _resolve_override_target(
    session: Session, schedule_id: int, payload: ScheduleOverrideRequest
) -> ResolvedOverrideTarget:
    sched = session.get(Schedule, schedule_id)
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )

    target_room_id = payload.room_id if payload.room_id is not None else sched.room_id
    target_slot_id = (
        payload.time_slot_id if payload.time_slot_id is not None else sched.time_slot_id
    )
    target_user_id = payload.user_id if payload.user_id is not None else sched.user_id

    room = session.get(Room, target_room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room {target_room_id} not found",
        )

    slot = session.get(TimeSlot, target_slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time slot {target_slot_id} not found",
        )

    user = session.get(User, target_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {target_user_id} not found",
        )

    course = session.get(Course, sched.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {sched.course_id} not found",
        )

    return ResolvedOverrideTarget(
        schedule=sched,
        course=course,
        room=room,
        slot=slot,
        user=user,
    )


def _validate_assignment_constraints(
    session: Session,
    semester_id: int,
    course: Course,
    room: Room,
    slot: TimeSlot,
    user: User,
    exclude_schedule_id: Optional[int] = None,
) -> None:
    if room.capacity < course.expected_enrollment:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Room '{room.room_number}' capacity ({room.capacity}) "
                f"is less than course '{course.course_code}' expected "
                f"enrollment ({course.expected_enrollment})"
            ),
        )

    if course.requires_lab and room.room_type.lower() != "lab":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Course '{course.course_code}' requires a lab room, but room "
                f"'{room.room_number}' has type '{room.room_type}'"
            ),
        )

    room_stmt = select(Schedule).where(
        Schedule.semester_id == semester_id,
        Schedule.room_id == room.id,
        Schedule.time_slot_id == slot.id,
    )
    if exclude_schedule_id is not None:
        room_stmt = room_stmt.where(Schedule.id != exclude_schedule_id)
    if session.exec(room_stmt).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Room '{room.room_number}' is already booked in time slot "
                f"{slot.id} for semester {semester_id}"
            ),
        )

    inst_stmt = select(Schedule).where(
        Schedule.semester_id == semester_id,
        Schedule.user_id == user.id,
        Schedule.time_slot_id == slot.id,
    )
    if exclude_schedule_id is not None:
        inst_stmt = inst_stmt.where(Schedule.id != exclude_schedule_id)
    if session.exec(inst_stmt).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Instructor '{user.full_name}' is already assigned to another "
                f"course in time slot {slot.id} for semester {semester_id}"
            ),
        )


def _validate_override_constraints(
    session: Session, target: ResolvedOverrideTarget
) -> None:
    _validate_assignment_constraints(
        session=session,
        semester_id=target.schedule.semester_id,
        course=target.course,
        room=target.room,
        slot=target.slot,
        user=target.user,
        exclude_schedule_id=target.schedule.id,
    )


def run_multi_semester_simulation(
    session: Session,
    semester_ids: List[int],
    max_courses_per_instructor: int = 2,
    min_courses_per_instructor: int = 1,
    reset_priorities_before_run: bool = True,
) -> MultiSemesterSimulationResponse:
    """
    Runs the CP-SAT solver sequentially across multiple semesters, carrying over
    dynamic instructor priority adjustments (+20,000 * (1 - sat_rate) compensation
    when <100% satisfied; -10,000 decay toward 100,000 when 100% satisfied) and
    persisting both schedule assignments and updated User.priority_score in SQLite.
    """
    if session.exec(select(Semester).limit(1)).first() is None:
        seed_database(session=session)

    if max_courses_per_instructor < min_courses_per_instructor:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Solver could not find a feasible schedule: teaching load bounds "
                "are over-constrained (INFEASIBLE)."
            ),
        )

    resolved_semesters: List[Semester] = []
    for sid in semester_ids:
        sem = session.exec(
            select(Semester).where((Semester.id == sid) | (Semester.semester_id == sid))
        ).first()
        if sem is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Semester {sid} does not exist",
            )
        resolved_semesters.append(sem)

    loader = DataLoader()
    if reset_priorities_before_run:
        for u in loader.users:
            u["priority_points"] = u.get("base_priority", BASE_PRIORITY)
        for db_user in session.exec(select(User)).all():
            db_user.priority_score = BASE_PRIORITY
            session.add(db_user)
        session.commit()
    else:
        db_scores = {u.id: u.priority_score for u in session.exec(select(User)).all()}
        for u in loader.users:
            if u["user_id"] in db_scores:
                u["priority_points"] = db_scores[u["user_id"]]

    slots = loader.get_slots_dict()
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]
    room_caps, course_enrolls, room_layouts = get_metadata(loader)
    valid_ic = loader.get_valid_ic_pairs()
    valid_rc = loader.get_valid_rc_pairs()

    inst_ids = {u["name"]: u["user_id"] for u in loader.get_instructors()}
    course_ids = {c["course_name"]: c["course_id"] for c in loader.courses}
    room_ids = {r["room_number"]: r["room_id"] for r in loader.rooms}

    results: List[SemesterSimulationResult] = []
    total_scheduled = 0
    total_wall = 0.0

    for sem in resolved_semesters:
        profiles = load_profiles_from_data(loader, semester_id=sem.semester_id)
        model, X, Y, Z, _ = build_schedule_model(
            profiles,
            DATE,
            class_room,
            instructors,
            courses,
            slots,
            seed=sem.semester_id,
            room_capacities=room_caps,
            course_enrollments=course_enrolls,
            room_layouts=room_layouts,
            valid_ic_pairs=valid_ic,
            valid_rc_pairs=valid_rc,
            min_courses_per_instructor=min_courses_per_instructor,
            max_courses_per_instructor=max_courses_per_instructor,
        )

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
        solve_status = solver.Solve(model)
        if solve_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Solver could not find a feasible schedule for semester {sem.id}."
                ),
            )

        status_str = "OPTIMAL" if solve_status == cp_model.OPTIMAL else "FEASIBLE"
        wall_time = round(solver.WallTime(), 4)
        total_wall += wall_time

        report = evaluate_satisfaction_and_update(
            solver,
            profiles,
            X,
            Y,
            Z,
            DATE,
            class_room,
            instructors,
            courses,
            slots,
            room_layouts=room_layouts,
            loader=loader,
        )

        rates = [
            r["satisfaction_rate"]
            for r in report.values()
            if r.get("has_preferences") and r.get("satisfaction_rate") is not None
        ]
        avg_satisfaction = round(sum(rates) / len(rates) * 100.0, 2) if rates else 100.0

        deltas: List[InstructorPriorityDelta] = []
        for inst_name, rep in report.items():
            uid = inst_ids[inst_name]
            db_user = session.get(User, uid)
            if db_user is not None:
                db_user.priority_score = rep["new_priority"]
                session.add(db_user)
            sat_pct = (
                round(rep["satisfaction_rate"] * 100.0, 2)
                if rep.get("satisfaction_rate") is not None
                else None
            )
            deltas.append(
                InstructorPriorityDelta(
                    user_id=uid,
                    instructor_name=inst_name,
                    old_priority=rep["old_priority"],
                    new_priority=rep["new_priority"],
                    delta=rep["delta"],
                    satisfaction_rate=sat_pct,
                )
            )

        existing_sched_ids = list(
            session.exec(
                select(Schedule.id).where(Schedule.semester_id == sem.id)
            ).all()
        )
        if existing_sched_ids:
            session.execute(
                delete(EditRequest).where(
                    EditRequest.schedule_id.in_(existing_sched_ids)
                )
            )
        session.execute(delete(Schedule).where(Schedule.semester_id == sem.id))
        scheduled_count = 0
        for c in courses:
            for i in instructors:
                if (i, c) not in Z or solver.Value(Z[i, c]) != 1:
                    continue
                placement = next(
                    (
                        (r, s)
                        for r in class_room
                        for s in slots
                        if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1
                    ),
                    None,
                )
                if placement is None:
                    continue
                room_number, slot_id = placement
                session.add(
                    Schedule(
                        semester_id=sem.id,
                        course_id=course_ids[c],
                        user_id=inst_ids[i],
                        room_id=room_ids[room_number],
                        time_slot_id=int(slot_id),
                        status="confirmed",
                    )
                )
                scheduled_count += 1

        session.commit()
        total_scheduled += scheduled_count
        results.append(
            SemesterSimulationResult(
                semester_id=sem.id,
                semester_name=sem.name,
                status=status_str,
                scheduled_count=scheduled_count,
                wall_time_seconds=wall_time,
                satisfaction_rate=avg_satisfaction,
                priority_updates=deltas,
            )
        )

    overall_sat = (
        round(sum(r.satisfaction_rate for r in results) / len(results), 2)
        if results
        else 100.0
    )
    final_priorities = {
        u["name"]: u.get("priority_points", BASE_PRIORITY)
        for u in loader.get_instructors()
    }

    return MultiSemesterSimulationResponse(
        semesters_simulated=len(results),
        total_scheduled_events=total_scheduled,
        average_satisfaction_rate=overall_sat,
        total_wall_time_seconds=round(total_wall, 4),
        results=results,
        final_priorities=final_priorities,
    )


def create_schedule_assignment(
    session: Session,
    payload: ScheduleCreateRequest,
) -> ScheduleEventResponse:
    """Create a manually scheduled course section after constraint validation."""
    sem = session.get(Semester, payload.semester_id)
    if sem is None:
        sem = session.exec(
            select(Semester).where(Semester.semester_id == payload.semester_id)
        ).first()
    if sem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester {payload.semester_id} not found",
        )

    course = session.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {payload.course_id} not found",
        )

    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.user_id} not found",
        )

    room = session.get(Room, payload.room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room {payload.room_id} not found",
        )

    slot = session.get(TimeSlot, payload.time_slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time slot {payload.time_slot_id} not found",
        )

    _validate_assignment_constraints(
        session=session,
        semester_id=sem.id,
        course=course,
        room=room,
        slot=slot,
        user=user,
    )

    sched = Schedule(
        semester_id=sem.id,
        course_id=course.id,
        user_id=user.id,
        room_id=room.id,
        time_slot_id=slot.id,
        status=payload.status or "confirmed",
    )
    session.add(sched)
    session.commit()
    session.refresh(sched)
    return build_schedule_event_response(session, sched)


def delete_schedule_assignment(
    session: Session,
    schedule_id: int,
) -> None:
    """Delete a scheduled section and any dependent edit requests."""
    sched = session.get(Schedule, schedule_id)
    if sched is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )
    session.execute(delete(EditRequest).where(EditRequest.schedule_id == schedule_id))
    session.delete(sched)
    session.commit()


def override_schedule_assignment(
    session: Session,
    schedule_id: int,
    payload: ScheduleOverrideRequest,
) -> ScheduleEventResponse:
    """
    Applies a coordinator manual override to an existing schedule row after
    enforcing foreign key existence (404), room capacity & lab type (422),
    and same-semester room/instructor slot collision checks (409).
    """
    target = _resolve_override_target(session, schedule_id, payload)
    _validate_override_constraints(session, target)

    sched = target.schedule
    sched.room_id = target.room.id
    sched.time_slot_id = target.slot.id
    sched.user_id = target.user.id
    sched.status = payload.status if payload.status is not None else "revised"

    session.add(sched)
    session.commit()
    session.refresh(sched)
    return build_schedule_event_response(session, sched)
