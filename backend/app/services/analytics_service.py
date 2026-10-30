from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.seeder import seed_database
from app.models.entities import (
    Course,
    InstructorPreference,
    Room,
    Schedule,
    Semester,
    TimeSlot,
    User,
)

UNDERUTILIZED_THRESHOLD_PCT = 25.0
HEAVILY_BOOKED_THRESHOLD_PCT = 75.0
STANDARD_COURSE_LOAD_LIMIT = 2


class InstructorFairnessItem(BaseModel):
    user_id: int
    instructor_name: str
    department: str
    priority_score: int
    assigned_courses_count: int
    preferred_day_matches: int
    preferred_room_matches: int
    satisfaction_rate: float


class DepartmentFairnessSummary(BaseModel):
    department: str
    instructor_count: int
    total_assigned_courses: int
    average_priority_score: float
    average_satisfaction_rate: float


class FairnessReportResponse(BaseModel):
    semester_id: int
    total_instructors: int
    total_scheduled_courses: int
    priority_gini_index: float = Field(
        description=(
            "Gini index of instructor priority scores (0.0 = perfect equality)"
        )
    )
    workload_gini_index: float = Field(
        description="Gini index of assigned course loads across instructors"
    )
    average_satisfaction_rate: float
    instructors: List[InstructorFairnessItem]
    departments: List[DepartmentFairnessSummary]


class RoomUtilizationItem(BaseModel):
    room_id: int
    room_number: str
    room_type: str
    capacity: int
    booked_slots_count: int
    total_available_slots: int
    slot_utilization_pct: float
    average_enrollment: float
    seat_occupancy_pct: float
    utilization_tier: str


class RoomUtilizationReportResponse(BaseModel):
    semester_id: int
    total_rooms: int
    total_time_slots: int
    overall_slot_utilization_pct: float
    overall_seat_occupancy_pct: float
    underutilized_rooms_count: int
    heavily_booked_rooms_count: int
    rooms: List[RoomUtilizationItem]


class ConflictViolationItem(BaseModel):
    violation_type: str
    severity: str
    schedule_ids: List[int]
    description: str
    room_number: Optional[str] = None
    instructor_name: Optional[str] = None
    course_code: Optional[str] = None
    time_slot_id: Optional[int] = None


class ConflictAuditResponse(BaseModel):
    semester_id: int
    total_schedules_audited: int
    is_conflict_free: bool
    hard_violation_count: int
    soft_warning_count: int
    violations: List[ConflictViolationItem]


def _compute_gini(values: List[float]) -> float:
    """Compute the Gini coefficient for a non-negative list of numbers."""
    cleaned = [max(0.0, float(v)) for v in values]
    n = len(cleaned)
    if n == 0:
        return 0.0
    total = sum(cleaned)
    if total == 0.0:
        return 0.0
    sorted_vals = sorted(cleaned)
    weighted_sum = sum((idx + 1) * val for idx, val in enumerate(sorted_vals))
    gini = (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n
    return round(max(0.0, min(1.0, gini)), 4)


def _classify_utilization_tier(slot_util_pct: float) -> str:
    if slot_util_pct < UNDERUTILIZED_THRESHOLD_PCT:
        return "underutilized"
    if slot_util_pct >= HEAVILY_BOOKED_THRESHOLD_PCT:
        return "heavily_booked"
    return "optimal"


def _matches_preferred_day(
    slot: Optional[TimeSlot], pref_days: Set[str]
) -> bool:
    if slot is None or not pref_days:
        return False
    return slot.day_pattern in pref_days or any(
        ch in pref_days for ch in slot.day_pattern
    )


def _ensure_semester_exists(session: Session, semester_id: int) -> Semester:
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
    return sem


def compute_fairness_metrics(
    session: Session, semester_id: int = 1
) -> FairnessReportResponse:
    """Compute instructor workload, satisfaction, and Gini fairness indices."""
    sem = _ensure_semester_exists(session, semester_id)

    instructors = session.exec(
        select(User).where(User.role == "instructor")
    ).all()
    schedules = session.exec(
        select(Schedule).where(Schedule.semester_id == sem.id)
    ).all()
    prefs = session.exec(
        select(InstructorPreference).where(
            InstructorPreference.semester_id == sem.id
        )
    ).all()
    rooms_by_id = {r.id: r for r in session.exec(select(Room)).all()}
    slots_by_id = {s.id: s for s in session.exec(select(TimeSlot)).all()}
    courses_by_id = {c.id: c for c in session.exec(select(Course)).all()}

    scheds_by_user: Dict[int, List[Schedule]] = defaultdict(list)
    for sc in schedules:
        scheds_by_user[sc.user_id].append(sc)

    prefs_by_user: Dict[int, InstructorPreference] = {}
    for pf in prefs:
        prefs_by_user[pf.user_id] = pf

    items: List[InstructorFairnessItem] = []
    dept_groups: Dict[str, List[InstructorFairnessItem]] = defaultdict(list)

    for inst in instructors:
        assigned = scheds_by_user.get(inst.id, [])
        pref = prefs_by_user.get(inst.id)
        pref_days = set(pref.preferred_days or []) if pref else set()
        pref_rooms = set(pref.preferred_rooms or []) if pref else set()

        resolved_dept = inst.department
        if assigned:
            first_course = courses_by_id.get(assigned[0].course_id)
            if first_course and first_course.department:
                resolved_dept = first_course.department

        day_matches = 0
        room_matches = 0
        checks = 0
        hits = 0

        for sc in assigned:
            slot = slots_by_id.get(sc.time_slot_id)
            room = rooms_by_id.get(sc.room_id)
            if pref_days:
                checks += 1
                if _matches_preferred_day(slot, pref_days):
                    day_matches += 1
                    hits += 1
            if pref_rooms:
                checks += 1
                if room and room.room_number in pref_rooms:
                    room_matches += 1
                    hits += 1

        if not assigned or checks == 0:
            sat_rate = 100.0
        else:
            sat_rate = round((hits / checks) * 100.0, 2)

        item = InstructorFairnessItem(
            user_id=inst.id,
            instructor_name=inst.full_name,
            department=resolved_dept,
            priority_score=inst.priority_score,
            assigned_courses_count=len(assigned),
            preferred_day_matches=day_matches,
            preferred_room_matches=room_matches,
            satisfaction_rate=sat_rate,
        )
        items.append(item)
        dept_groups[resolved_dept].append(item)

    dept_summaries: List[DepartmentFairnessSummary] = []
    for dept_name in sorted(dept_groups.keys()):
        group = dept_groups[dept_name]
        avg_prio = round(
            sum(i.priority_score for i in group) / len(group), 2
        )
        avg_sat = round(
            sum(i.satisfaction_rate for i in group) / len(group), 2
        )
        dept_summaries.append(
            DepartmentFairnessSummary(
                department=dept_name,
                instructor_count=len(group),
                total_assigned_courses=sum(
                    i.assigned_courses_count for i in group
                ),
                average_priority_score=avg_prio,
                average_satisfaction_rate=avg_sat,
            )
        )

    priority_gini = _compute_gini([i.priority_score for i in items])
    workload_gini = _compute_gini([i.assigned_courses_count for i in items])
    overall_sat = (
        round(sum(i.satisfaction_rate for i in items) / len(items), 2)
        if items
        else 100.0
    )

    return FairnessReportResponse(
        semester_id=sem.id,
        total_instructors=len(items),
        total_scheduled_courses=len(schedules),
        priority_gini_index=priority_gini,
        workload_gini_index=workload_gini,
        average_satisfaction_rate=overall_sat,
        instructors=items,
        departments=dept_summaries,
    )


def compute_room_utilization(
    session: Session, semester_id: int = 1
) -> RoomUtilizationReportResponse:
    """Compute per-room slot utilization and seat occupancy percentages."""
    sem = _ensure_semester_exists(session, semester_id)

    rooms = session.exec(select(Room)).all()
    slots = session.exec(select(TimeSlot)).all()
    schedules = session.exec(
        select(Schedule).where(Schedule.semester_id == sem.id)
    ).all()
    courses_by_id = {c.id: c for c in session.exec(select(Course)).all()}

    total_slots = max(1, len(slots))
    scheds_by_room: Dict[int, List[Schedule]] = defaultdict(list)
    for sc in schedules:
        scheds_by_room[sc.room_id].append(sc)

    room_items: List[RoomUtilizationItem] = []
    underutilized_count = 0
    heavily_booked_count = 0

    for room in rooms:
        assigned = scheds_by_room.get(room.id, [])
        booked_count = len(assigned)
        slot_util = round((booked_count / total_slots) * 100.0, 2)

        if assigned:
            enrollments = [
                courses_by_id[sc.course_id].expected_enrollment
                for sc in assigned
                if sc.course_id in courses_by_id
            ]
            avg_enroll = (
                round(sum(enrollments) / len(enrollments), 2)
                if enrollments
                else 0.0
            )
            seat_occ = (
                round(min(100.0, (avg_enroll / room.capacity) * 100.0), 2)
                if room.capacity > 0
                else 0.0
            )
        else:
            avg_enroll = 0.0
            seat_occ = 0.0

        tier = _classify_utilization_tier(slot_util)
        if tier == "underutilized":
            underutilized_count += 1
        elif tier == "heavily_booked":
            heavily_booked_count += 1

        room_items.append(
            RoomUtilizationItem(
                room_id=room.id,
                room_number=room.room_number,
                room_type=room.room_type,
                capacity=room.capacity,
                booked_slots_count=booked_count,
                total_available_slots=total_slots,
                slot_utilization_pct=slot_util,
                average_enrollment=avg_enroll,
                seat_occupancy_pct=seat_occ,
                utilization_tier=tier,
            )
        )

    overall_slot_util = (
        round(
            sum(r.slot_utilization_pct for r in room_items) / len(room_items), 2
        )
        if room_items
        else 0.0
    )
    active_rooms = [r for r in room_items if r.booked_slots_count > 0]
    overall_seat_occ = (
        round(
            sum(r.seat_occupancy_pct for r in active_rooms) / len(active_rooms),
            2,
        )
        if active_rooms
        else 0.0
    )

    return RoomUtilizationReportResponse(
        semester_id=sem.id,
        total_rooms=len(room_items),
        total_time_slots=len(slots),
        overall_slot_utilization_pct=overall_slot_util,
        overall_seat_occupancy_pct=overall_seat_occ,
        underutilized_rooms_count=underutilized_count,
        heavily_booked_rooms_count=heavily_booked_count,
        rooms=room_items,
    )


def audit_schedule_conflicts(
    session: Session, semester_id: int = 1
) -> ConflictAuditResponse:
    """Scan schedules in a semester for hard conflicts and overload warnings."""
    sem = _ensure_semester_exists(session, semester_id)

    schedules = session.exec(
        select(Schedule).where(Schedule.semester_id == sem.id)
    ).all()
    rooms_by_id = {r.id: r for r in session.exec(select(Room)).all()}
    users_by_id = {u.id: u for u in session.exec(select(User)).all()}
    courses_by_id = {c.id: c for c in session.exec(select(Course)).all()}

    violations: List[ConflictViolationItem] = []
    hard_count = 0
    soft_count = 0

    room_slot_map: Dict[Tuple[int, int], List[Schedule]] = defaultdict(list)
    user_slot_map: Dict[Tuple[int, int], List[Schedule]] = defaultdict(list)
    user_load_map: Dict[int, List[Schedule]] = defaultdict(list)

    for sc in schedules:
        room_slot_map[(sc.room_id, sc.time_slot_id)].append(sc)
        user_slot_map[(sc.user_id, sc.time_slot_id)].append(sc)
        user_load_map[sc.user_id].append(sc)

        room = rooms_by_id.get(sc.room_id)
        course = courses_by_id.get(sc.course_id)
        if room and course:
            if course.expected_enrollment > room.capacity:
                hard_count += 1
                violations.append(
                    ConflictViolationItem(
                        violation_type="CAPACITY_OVERFLOW",
                        severity="hard",
                        schedule_ids=[sc.id],
                        room_number=room.room_number,
                        course_code=course.course_code,
                        time_slot_id=sc.time_slot_id,
                        description=(
                            f"Course '{course.course_code}' enrollment "
                            f"({course.expected_enrollment}) exceeds room "
                            f"'{room.room_number}' capacity ({room.capacity})"
                        ),
                    )
                )
            if course.requires_lab and room.room_type.lower() != "lab":
                hard_count += 1
                violations.append(
                    ConflictViolationItem(
                        violation_type="LAB_TYPE_MISMATCH",
                        severity="hard",
                        schedule_ids=[sc.id],
                        room_number=room.room_number,
                        course_code=course.course_code,
                        time_slot_id=sc.time_slot_id,
                        description=(
                            f"Lab course '{course.course_code}' is assigned to "
                            f"non-lab room '{room.room_number}' ({room.room_type})"
                        ),
                    )
                )

    for (room_id, slot_id), group in room_slot_map.items():
        if len(group) > 1:
            hard_count += 1
            room = rooms_by_id.get(room_id)
            r_num = room.room_number if room else f"Room #{room_id}"
            violations.append(
                ConflictViolationItem(
                    violation_type="ROOM_DOUBLE_BOOKING",
                    severity="hard",
                    schedule_ids=[g.id for g in group],
                    room_number=r_num,
                    time_slot_id=slot_id,
                    description=(
                        f"Room '{r_num}' has {len(group)} courses booked "
                        f"simultaneously in time slot {slot_id}"
                    ),
                )
            )

    for (user_id, slot_id), group in user_slot_map.items():
        if len(group) > 1:
            hard_count += 1
            user = users_by_id.get(user_id)
            u_name = user.full_name if user else f"User #{user_id}"
            violations.append(
                ConflictViolationItem(
                    violation_type="INSTRUCTOR_DOUBLE_BOOKING",
                    severity="hard",
                    schedule_ids=[g.id for g in group],
                    instructor_name=u_name,
                    time_slot_id=slot_id,
                    description=(
                        f"Instructor '{u_name}' is assigned to {len(group)} "
                        f"courses simultaneously in time slot {slot_id}"
                    ),
                )
            )

    for user_id, group in user_load_map.items():
        if len(group) > STANDARD_COURSE_LOAD_LIMIT:
            soft_count += 1
            user = users_by_id.get(user_id)
            u_name = user.full_name if user else f"User #{user_id}"
            violations.append(
                ConflictViolationItem(
                    violation_type="INSTRUCTOR_OVERLOAD_WARNING",
                    severity="soft",
                    schedule_ids=[g.id for g in group],
                    instructor_name=u_name,
                    description=(
                        f"Instructor '{u_name}' is assigned {len(group)} courses "
                        f"(exceeds standard 2-course load)"
                    ),
                )
            )

    return ConflictAuditResponse(
        semester_id=sem.id,
        total_schedules_audited=len(schedules),
        is_conflict_free=(hard_count == 0),
        hard_violation_count=hard_count,
        soft_warning_count=soft_count,
        violations=violations,
    )
