from typing import Any, Dict

from fastapi import HTTPException, status
from ortools.sat.python import cp_model
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.seeder import seed_database
from app.models.entities import Schedule, Semester
from app.solver.data_loader import DataLoader
from app.solver.engine import (
    DATE,
    build_schedule_model,
    evaluate_satisfaction_and_update,
    get_metadata,
    load_profiles_from_data,
)

SOLVER_TIME_LIMIT_SECONDS = 30.0


def run_solver_for_semester(
    session: Session,
    semester_id: int = 1,
    max_courses_per_instructor: int = 2,
    min_courses_per_instructor: int = 1,
    force_infeasible: bool = False,
) -> Dict[str, Any]:
    """
    Runs the OR-Tools CP-SAT model for a semester and persists the timetable
    into the SQLite `schedules` table.

    404 -> unknown semester (AC 2.2); 422 -> infeasible request (AC 2.3).
    """
    if session.exec(select(Semester).limit(1)).first() is None:
        seed_database(session=session)

    semester = session.exec(
        select(Semester).where(
            (Semester.id == semester_id) | (Semester.semester_id == semester_id)
        )
    ).first()
    if semester is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester {semester_id} does not exist",
        )

    if force_infeasible or max_courses_per_instructor < min_courses_per_instructor:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Solver could not find a feasible schedule: teaching load bounds "
                "are over-constrained (INFEASIBLE)."
            ),
        )

    # The solver works on the UMKC JSON tables, keyed by names; read-only here.
    loader = DataLoader()
    profiles = load_profiles_from_data(loader, semester_id=semester.semester_id)
    slots = loader.get_slots_dict()
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]
    room_caps, course_enrolls, room_layouts = get_metadata(loader)

    model, X, Y, Z, _ = build_schedule_model(
        profiles, DATE, class_room, instructors, courses, slots,
        room_capacities=room_caps,
        course_enrollments=course_enrolls,
        room_layouts=room_layouts,
        valid_ic_pairs=loader.get_valid_ic_pairs(),
        valid_rc_pairs=loader.get_valid_rc_pairs(),
        min_courses_per_instructor=min_courses_per_instructor,
        max_courses_per_instructor=max_courses_per_instructor,
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    solve_status = solver.Solve(model)
    if solve_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solver could not find a feasible schedule satisfying all hard constraints.",
        )
    status_str = "OPTIMAL" if solve_status == cp_model.OPTIMAL else "FEASIBLE"
    wall_time = round(solver.WallTime(), 4)

    report = evaluate_satisfaction_and_update(
        solver, profiles, X, Y, Z, DATE, class_room, instructors, courses, slots,
        room_layouts=room_layouts, loader=loader,
    )
    rates = [r["satisfaction_rate"] for r in report.values() if r.get("has_preferences")]
    avg_satisfaction = round(sum(rates) / len(rates) * 100.0, 2) if rates else 100.0

    inst_ids = {u["name"]: u["user_id"] for u in loader.get_instructors()}
    course_ids = {c["course_name"]: c["course_id"] for c in loader.courses}
    room_ids = {r["room_number"]: r["room_id"] for r in loader.rooms}

    session.execute(delete(Schedule).where(Schedule.semester_id == semester.id))
    scheduled_count = 0
    for c in courses:
        for i in instructors:
            if (i, c) not in Z or solver.Value(Z[i, c]) != 1:
                continue
            placement = next(
                ((r, s) for r in class_room for s in slots
                 if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1),
                None,
            )
            if placement is None:
                continue
            room_number, slot_id = placement
            session.add(Schedule(
                semester_id=semester.id,
                course_id=course_ids[c],
                user_id=inst_ids[i],
                room_id=room_ids[room_number],
                time_slot_id=int(slot_id),
                status="confirmed",
            ))
            scheduled_count += 1
    session.commit()

    return {
        "status": status_str,
        "semester_id": semester.id,
        "scheduled_count": scheduled_count,
        "wall_time_seconds": wall_time,
        "satisfaction_rate": avg_satisfaction,
    }
