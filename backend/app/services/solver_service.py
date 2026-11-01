import re
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from ortools.sat.python import cp_model
from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.seeder import (
    days_to_day_pattern,
    resolve_or_create_time_slot,
    seed_database,
)
from app.models.entities import (
    Course,
    EditRequest,
    InstructorCourseAssignment,
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
FALLBACK_TIME_LIMIT_SECONDS = 5.0

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

    ordered_prefs = [p for p in prefs if p.course_id is not None] + [
        p for p in prefs if p.course_id is None
    ]
    for pref in ordered_prefs:
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
            general_prefs["days"] = days
            general_prefs["slots"] = slots
            general_prefs["classrooms"] = rooms
            profiles[inst_name]["course_preferences"] = {}
        else:
            course_name = db_course_by_id.get(
                pref.course_id
            ) or loader_course_by_id.get(pref.course_id)
            if course_name and course_name in loader_course_names:
                course_prefs = profiles[inst_name].setdefault(
                    "course_preferences", {}
                )
                existing = course_prefs.get(course_name, {})
                course_prefs[course_name] = {
                    "days": days,
                    "slots": slots,
                    "classrooms": rooms,
                    "layout": existing.get("layout"),
                }
                valid_ic_pairs.add((inst_name, course_name))


def _resolve_pinned_assignments(
    session: Session,
    semester_id: int,
    loader: DataLoader,
    instructors: List[str],
    courses: List[str],
    valid_ic_pairs: Set[Tuple[str, str]],
    valid_rc_pairs: Set[Tuple[str, str]],
) -> Tuple[
    List[Tuple[str, str]],
    Dict[int, List[int]],
    Dict[str, int],
    Dict[str, int],
]:
    rows = session.exec(
        select(InstructorCourseAssignment)
        .where(InstructorCourseAssignment.semester_id == semester_id)
        .order_by(InstructorCourseAssignment.id)
    ).all()
    if not rows:
        return [], {}, {}, {}

    user_name_by_id = {
        u.id: u.full_name
        for u in session.exec(select(User)).all()
        if u.id is not None
    }
    loader_inst_by_id = {u["user_id"]: u["name"] for u in loader.get_instructors()}
    db_course_by_id = {
        c.id: c.course_name
        for c in session.exec(select(Course)).all()
        if c.id is not None
    }
    loader_course_by_id = {c["course_id"]: c["course_name"] for c in loader.courses}

    instructors_set = set(instructors)
    courses_set = set(courses)
    courses_with_rc = {c_name for (_r_num, c_name) in valid_rc_pairs}

    pinned_ic_pairs: List[Tuple[str, str]] = []
    pinned_by_course: Dict[str, int] = {}
    pinned_by_inst: Dict[str, int] = {}
    assigned_user_ids_by_course: Dict[int, List[int]] = {}

    for row in rows:
        uid_list = assigned_user_ids_by_course.setdefault(row.course_id, [])
        if row.user_id not in uid_list:
            uid_list.append(row.user_id)

        inst_name = loader_inst_by_id.get(row.user_id) or user_name_by_id.get(
            row.user_id
        )
        course_name = loader_course_by_id.get(row.course_id) or db_course_by_id.get(
            row.course_id
        )
        if (
            not inst_name
            or not course_name
            or inst_name not in instructors_set
            or course_name not in courses_set
        ):
            continue

        valid_ic_pairs.add((inst_name, course_name))
        if (
            (inst_name, course_name) not in pinned_ic_pairs
            and course_name in courses_with_rc
            and pinned_by_course.get(course_name, 0) < 2
        ):
            pinned_ic_pairs.append((inst_name, course_name))
            pinned_by_course[course_name] = pinned_by_course.get(course_name, 0) + 1
            pinned_by_inst[inst_name] = pinned_by_inst.get(inst_name, 0) + 1

    return (
        pinned_ic_pairs,
        assigned_user_ids_by_course,
        pinned_by_course,
        pinned_by_inst,
    )


def _expand_subject_cluster_pairs(
    base_valid_ic: Set[Tuple[str, str]],
    pinned_ic_pairs: List[Tuple[str, str]],
    courses: List[str],
) -> Set[Tuple[str, str]]:
    inst_prefixes: Dict[str, Set[str]] = {}
    for inst_name, course_name in base_valid_ic:
        parts = course_name.split()
        if parts:
            inst_prefixes.setdefault(inst_name, set()).add(parts[0])

    pinned_prefixes = {
        c_name.split()[0] for (_i_name, c_name) in pinned_ic_pairs if c_name.split()
    }
    expanded = set(base_valid_ic)
    for inst_name, prefixes in inst_prefixes.items():
        shared = prefixes & pinned_prefixes
        if not shared:
            continue
        for course_name in courses:
            parts = course_name.split()
            if parts and parts[0] in shared:
                expanded.add((inst_name, course_name))
    return expanded


def _has_slot_conflict(
    entity_id: Optional[int],
    candidate: TimeSlot,
    occupied: Set[Tuple[int, int]],
    slots_by_id: Dict[int, TimeSlot],
) -> bool:
    if entity_id is None or candidate.id is None:
        return True
    if (entity_id, candidate.id) in occupied:
        return True
    cand_days = set(days_to_day_pattern([candidate.day_pattern]))
    cand_start = _to_minutes(candidate.start_time)
    cand_end = _to_minutes(candidate.end_time)
    for occ_entity_id, occ_slot_id in occupied:
        if occ_entity_id != entity_id:
            continue
        occ = slots_by_id.get(occ_slot_id)
        if occ is None:
            continue
        occ_days = set(days_to_day_pattern([occ.day_pattern]))
        if not (cand_days & occ_days):
            continue
        if (
            cand_start < _to_minutes(occ.end_time)
            and _to_minutes(occ.start_time) < cand_end
        ):
            return True
    return False


def _schedule_extra_sqlite_courses(
    session: Session,
    semester_id: int,
    json_course_ids: Set[int],
    json_course_names: Set[str],
    occupied_room_slots: Set[Tuple[int, int]],
    occupied_inst_slots: Set[Tuple[int, int]],
    inst_load: Dict[int, int],
    assigned_user_ids_by_course: Optional[Dict[int, List[int]]] = None,
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

    slots_by_id = {s.id: s for s in all_slots if s.id is not None}
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

        assigned_ids = (
            assigned_user_ids_by_course.get(extra.id, [])
            if assigned_user_ids_by_course and extra.id is not None
            else []
        )
        assigned_rank = {uid: idx for idx, uid in enumerate(assigned_ids)}
        dept_upper = extra.department.upper()
        ranked_instructors = sorted(
            all_instructors,
            key=lambda u: (
                0 if u.id in assigned_rank else 1,
                assigned_rank.get(u.id, 0),
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
                if _has_slot_conflict(
                    room.id, slot, occupied_room_slots, slots_by_id
                ):
                    continue
                chosen_inst = next(
                    (
                        inst
                        for inst in ranked_instructors
                        if not _has_slot_conflict(
                            inst.id, slot, occupied_inst_slots, slots_by_id
                        )
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

    loader = DataLoader()
    profiles = load_profiles_from_data(loader, semester_id=semester.semester_id)
    base_valid_ic = set(loader.get_valid_ic_pairs())
    valid_ic_pairs = set(base_valid_ic)
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
    valid_rc_pairs = loader.get_valid_rc_pairs()

    (
        pinned_ic_pairs,
        assigned_user_ids_by_course,
        pinned_by_course,
        pinned_by_inst,
    ) = _resolve_pinned_assignments(
        session=session,
        semester_id=semester.id,
        loader=loader,
        instructors=instructors,
        courses=courses,
        valid_ic_pairs=valid_ic_pairs,
        valid_rc_pairs=valid_rc_pairs,
    )
    max_pinned_per_inst = max(pinned_by_inst.values(), default=0)
    effective_max_courses = max(max_courses_per_instructor, max_pinned_per_inst)
    total_min_load = sum(
        max(min_courses_per_instructor, pinned_by_inst.get(inst_name, 0))
        for inst_name in instructors
    )
    target_total_sections = sum(
        max(1, pinned_by_course.get(c_name, 0)) for c_name in courses
    )

    def _build_and_solve(
        ic_pairs: Set[Tuple[str, str]],
        time_limit: float,
    ) -> Tuple[
        cp_model.CpSolver,
        int,
        Any,
        Any,
        Any,
    ]:
        built_model, built_x, built_y, built_z, _ = build_schedule_model(
            profiles,
            DATE,
            class_room,
            instructors,
            courses,
            slots,
            room_capacities=room_caps,
            course_enrollments=course_enrolls,
            room_layouts=room_layouts,
            valid_ic_pairs=ic_pairs,
            valid_rc_pairs=valid_rc_pairs,
            min_courses_per_instructor=min_courses_per_instructor,
            max_courses_per_instructor=effective_max_courses,
        )
        for inst_name, course_name in pinned_ic_pairs:
            if (inst_name, course_name) in built_z:
                built_model.Add(built_z[inst_name, course_name] == 1)

        if effective_max_courses > max_courses_per_instructor:
            for inst_name in instructors:
                inst_cap = max(
                    max_courses_per_instructor,
                    pinned_by_inst.get(inst_name, 0),
                )
                if inst_cap < effective_max_courses:
                    qual_courses = [
                        c_name
                        for c_name in courses
                        if (inst_name, c_name) in built_z
                    ]
                    if qual_courses:
                        built_model.Add(
                            sum(built_z[inst_name, c_name] for c_name in qual_courses)
                            <= inst_cap
                        )
            if target_total_sections >= total_min_load:
                for c_name in courses:
                    qual_insts = [
                        inst_name
                        for inst_name in instructors
                        if (inst_name, c_name) in built_z
                    ]
                    if qual_insts:
                        built_model.Add(
                            sum(built_z[inst_name, c_name] for inst_name in qual_insts)
                            == max(1, pinned_by_course.get(c_name, 0))
                        )

        cp_solver = cp_model.CpSolver()
        cp_solver.parameters.max_time_in_seconds = time_limit
        st = cp_solver.Solve(built_model)
        return cp_solver, st, built_x, built_y, built_z

    solver, solve_status, X, Y, Z = _build_and_solve(
        valid_ic_pairs, SOLVER_TIME_LIMIT_SECONDS
    )
    if solve_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE) and pinned_ic_pairs:
        expanded_ic = _expand_subject_cluster_pairs(
            base_valid_ic | valid_ic_pairs, pinned_ic_pairs, courses
        )
        solver, solve_status, X, Y, Z = _build_and_solve(
            expanded_ic, FALLBACK_TIME_LIMIT_SECONDS
        )

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

    slot_times_by_id = {
        int(ts["slot_id"]): (
            str(ts["start_time"]).strip(),
            str(ts["end_time"]).strip(),
        )
        for ts in loader.time_slots
    }
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
                or sid not in slot_times_by_id
            ):
                continue
            chosen_days = [
                d
                for d in DATE
                if (d, room_number, slot_id, i, c) in X
                and solver.Value(X[d, room_number, slot_id, i, c]) == 1
            ]
            day_pattern = days_to_day_pattern(chosen_days, default="TR")
            start_time, end_time = slot_times_by_id[sid]
            resolved_slot = resolve_or_create_time_slot(
                session, start_time, end_time, day_pattern
            )
            session.add(
                Schedule(
                    semester_id=semester.id,
                    course_id=cid,
                    user_id=uid,
                    room_id=rid,
                    time_slot_id=resolved_slot.id,
                    status="confirmed",
                )
            )
            occupied_room_slots.add((rid, resolved_slot.id))
            occupied_inst_slots.add((uid, resolved_slot.id))
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
        assigned_user_ids_by_course=assigned_user_ids_by_course,
    )
    session.commit()

    return {
        "status": status_str,
        "semester_id": semester.id,
        "scheduled_count": scheduled_count,
        "wall_time_seconds": wall_time,
        "satisfaction_rate": avg_satisfaction,
    }
