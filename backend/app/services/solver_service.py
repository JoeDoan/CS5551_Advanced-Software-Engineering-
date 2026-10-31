import re
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from ortools.sat.python import cp_model
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.seeder import seed_database
from app.models.entities import (
    Course,
    EditRequest,
    InstructorPreference,
    Room,
    Schedule,
    Semester,
    TimeSlot,
    User,
)
from app.solver.data_loader import DataLoader
from app.solver.engine import (
    DATE,
    build_schedule_model,
    evaluate_satisfaction_and_update,
    get_metadata,
    load_profiles_from_data,
)

SOLVER_TIME_LIMIT_SECONDS = 30.0

_DAY_CODE_MAP = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
}
_DATE_BY_UPPER = {day.upper(): day for day in DATE}
_TIME_RANGE_RE = re.compile(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})")


def _to_minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":", 1)
    return int(hours) * 60 + int(mins)


def _expand_preferred_days(raw_days: Any) -> List[str]:
    if not isinstance(raw_days, list):
        return []
    expanded: List[str] = []
    for item in raw_days:
        token = str(item).strip()
        if not token:
            continue
        upper = token.upper()
        if upper in _DATE_BY_UPPER:
            day_name = _DATE_BY_UPPER[upper]
            if day_name not in expanded:
                expanded.append(day_name)
        elif all(ch in _DAY_CODE_MAP for ch in upper):
            for ch in upper:
                day_name = _DAY_CODE_MAP[ch]
                if day_name not in expanded:
                    expanded.append(day_name)
    return expanded


def _map_preferred_slots(raw_slots: Any, loader: DataLoader) -> List[int]:
    if not isinstance(raw_slots, list):
        return []

    exact_by_label: Dict[str, int] = {}
    windows: List[Tuple[int, int, int]] = []
    valid_ids: Set[int] = set()
    for ts in loader.time_slots:
        sid = int(ts["slot_id"])
        start = str(ts["start_time"]).strip()
        end = str(ts["end_time"]).strip()
        valid_ids.add(sid)
        exact_by_label[f"{start}-{end}"] = sid
        windows.append((sid, _to_minutes(start), _to_minutes(end)))

    mapped: List[int] = []
    for item in raw_slots:
        resolved: Optional[int] = None
        if isinstance(item, int) and item in valid_ids:
            resolved = item
        else:
            token = str(item).strip()
            if token.isdigit() and int(token) in valid_ids:
                resolved = int(token)
            else:
                match = _TIME_RANGE_RE.search(token)
                if match:
                    start_s, end_s = match.group(1), match.group(2)
                    label = f"{start_s}-{end_s}"
                    if label in exact_by_label:
                        resolved = exact_by_label[label]
                    else:
                        s_min = _to_minutes(start_s)
                        e_min = _to_minutes(end_s)
                        best_overlap = 0
                        for sid, w_start, w_end in windows:
                            overlap = min(e_min, w_end) - max(s_min, w_start)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                resolved = sid
        if resolved is not None and resolved not in mapped:
            mapped.append(resolved)
    return mapped


def _overlay_sqlite_preferences(
    session: Session,
    semester_id: int,
    profiles: Dict[str, Any],
    valid_ic_pairs: Set[Tuple[str, str]],
    loader: DataLoader,
) -> None:
    prefs = session.exec(
        select(InstructorPreference)
        .where(InstructorPreference.semester_id == semester_id)
        .order_by(InstructorPreference.id)
    ).all()
    if not prefs:
        return

    user_name_by_id = {
        u.id: u.full_name
        for u in session.exec(select(User)).all()
        if u.id is not None
    }
    loader_course_names = {c["course_name"] for c in loader.courses}
    loader_course_by_id = {c["course_id"]: c["course_name"] for c in loader.courses}
    db_course_by_id = {
        c.id: c.course_name
        for c in session.exec(select(Course)).all()
        if c.id is not None
    }

    for pref in prefs:
        inst_name = user_name_by_id.get(pref.user_id)
        if not inst_name or inst_name not in profiles:
            continue

        days = _expand_preferred_days(pref.preferred_days)
        slots = _map_preferred_slots(pref.preferred_slots, loader)
        rooms = (
            [str(r).strip() for r in pref.preferred_rooms if str(r).strip()]
            if isinstance(pref.preferred_rooms, list)
            else []
        )

        if pref.course_id is None:
            general_prefs = profiles[inst_name].setdefault(
                "preferences",
                {"days": [], "slots": [], "classrooms": [], "layout": None},
            )
            if days:
                general_prefs["days"] = days
            if slots:
                general_prefs["slots"] = slots
            if rooms:
                general_prefs["classrooms"] = rooms
        else:
            course_name = db_course_by_id.get(pref.course_id) or loader_course_by_id.get(
                pref.course_id
            )
            if course_name and course_name in loader_course_names:
                course_prefs = profiles[inst_name].setdefault("course_preferences", {})
                existing = course_prefs.get(course_name, {})
                course_prefs[course_name] = {
                    "days": days,
                    "slots": slots,
                    "classrooms": rooms,
                    "layout": existing.get("layout"),
                }
                valid_ic_pairs.add((inst_name, course_name))


def _schedule_extra_sqlite_courses(
    session: Session,
    semester_id: int,
    json_course_ids: Set[int],
    json_course_names: Set[str],
    occupied_room_slots: Set[Tuple[int, int]],
    occupied_inst_slots: Set[Tuple[int, int]],
    inst_load: Dict[int, int],
) -> int:
    all_courses = session.exec(select(Course).order_by(Course.id)).all()
    extra_courses = [
        course
        for course in all_courses
        if course.id not in json_course_ids
        and course.course_name not in json_course_names
    ]
    if not extra_courses:
        return 0

    all_rooms = session.exec(select(Room).order_by(Room.capacity, Room.id)).all()
    all_slots = session.exec(select(TimeSlot).order_by(TimeSlot.id)).all()
    all_instructors = session.exec(
        select(User).where(User.role == "instructor").order_by(User.id)
    ).all()
    if not all_rooms or not all_slots or not all_instructors:
        return 0

    added = 0
    for extra in extra_courses:
        eligible_rooms = [
            room
            for room in all_rooms
            if room.capacity >= extra.expected_enrollment
            and (not extra.requires_lab or room.room_type.lower() == "lab")
        ]
        if not eligible_rooms:
            continue

        dept_upper = extra.department.upper()
        ranked_instructors = sorted(
            all_instructors,
            key=lambda u: (
                0 if u.department.upper() == dept_upper else 1,
                inst_load.get(u.id, 0),
                u.id or 0,
            ),
        )

        placed = False
        for slot in all_slots:
            if placed:
                break
            for room in eligible_rooms:
                if (room.id, slot.id) in occupied_room_slots:
                    continue
                chosen_inst = next(
                    (
                        inst
                        for inst in ranked_instructors
                        if (inst.id, slot.id) not in occupied_inst_slots
                    ),
                    None,
                )
                if chosen_inst is None:
                    continue
                session.add(
                    Schedule(
                        semester_id=semester_id,
                        course_id=extra.id,
                        user_id=chosen_inst.id,
                        room_id=room.id,
                        time_slot_id=slot.id,
                        status="confirmed",
                    )
                )
                occupied_room_slots.add((room.id, slot.id))
                occupied_inst_slots.add((chosen_inst.id, slot.id))
                inst_load[chosen_inst.id] = inst_load.get(chosen_inst.id, 0) + 1
                added += 1
                placed = True
                break

    return added


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
    valid_ic_pairs = set(loader.get_valid_ic_pairs())
    _overlay_sqlite_preferences(
        session=session,
        semester_id=semester.id,
        profiles=profiles,
        valid_ic_pairs=valid_ic_pairs,
        loader=loader,
    )
    slots = loader.get_slots_dict()
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]
    room_caps, course_enrolls, room_layouts = get_metadata(loader)

    model, X, Y, Z, _ = build_schedule_model(
        profiles,
        DATE,
        class_room,
        instructors,
        courses,
        slots,
        room_capacities=room_caps,
        course_enrollments=course_enrolls,
        room_layouts=room_layouts,
        valid_ic_pairs=valid_ic_pairs,
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
            detail=(
                "Solver could not find a feasible schedule satisfying all "
                "hard constraints."
            ),
        )
    status_str = "OPTIMAL" if solve_status == cp_model.OPTIMAL else "FEASIBLE"
    wall_time = round(solver.WallTime(), 4)

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
        r["satisfaction_rate"] for r in report.values() if r.get("has_preferences")
    ]
    avg_satisfaction = round(sum(rates) / len(rates) * 100.0, 2) if rates else 100.0

    inst_ids = {u["name"]: u["user_id"] for u in loader.get_instructors()}
    course_ids = {c["course_name"]: c["course_id"] for c in loader.courses}
    room_ids = {r["room_number"]: r["room_id"] for r in loader.rooms}

    db_course_ids = {c.id for c in session.exec(select(Course)).all()}
    db_room_ids = {r.id for r in session.exec(select(Room)).all()}
    db_user_ids = {u.id for u in session.exec(select(User)).all()}

    old_sched_ids = list(
        session.exec(
            select(Schedule.id).where(Schedule.semester_id == semester.id)
        ).all()
    )
    if old_sched_ids:
        session.execute(
            delete(EditRequest).where(EditRequest.schedule_id.in_(old_sched_ids))
        )
    session.execute(delete(Schedule).where(Schedule.semester_id == semester.id))

    occupied_room_slots: Set[Tuple[int, int]] = set()
    occupied_inst_slots: Set[Tuple[int, int]] = set()
    inst_load: Dict[int, int] = {}
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
            cid = course_ids[c]
            uid = inst_ids[i]
            rid = room_ids[room_number]
            sid = int(slot_id)
            if (
                cid not in db_course_ids
                or uid not in db_user_ids
                or rid not in db_room_ids
            ):
                continue
            session.add(
                Schedule(
                    semester_id=semester.id,
                    course_id=cid,
                    user_id=uid,
                    room_id=rid,
                    time_slot_id=sid,
                    status="confirmed",
                )
            )
            occupied_room_slots.add((rid, sid))
            occupied_inst_slots.add((uid, sid))
            inst_load[uid] = inst_load.get(uid, 0) + 1
            scheduled_count += 1

    scheduled_count += _schedule_extra_sqlite_courses(
        session=session,
        semester_id=semester.id,
        json_course_ids=set(course_ids.values()),
        json_course_names=set(course_ids.keys()),
        occupied_room_slots=occupied_room_slots,
        occupied_inst_slots=occupied_inst_slots,
        inst_load=inst_load,
    )
    session.commit()

    return {
        "status": status_str,
        "semester_id": semester.id,
        "scheduled_count": scheduled_count,
        "wall_time_seconds": wall_time,
        "satisfaction_rate": avg_satisfaction,
    }
