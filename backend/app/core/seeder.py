import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.core.database import engine, init_db
from app.models.entities import (
    Building,
    Campus,
    Course,
    EditRequest,
    InstructorPreference,
    Room,
    Schedule,
    Semester,
    TimeSlot,
    User,
)

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_CORE_DIR))
DEFAULT_DATA_DIR = os.path.join(_BACKEND_DIR, "data", "umkc")

DAY_NAME_TO_CODE = {
    "MONDAY": "M",
    "TUESDAY": "T",
    "WEDNESDAY": "W",
    "THURSDAY": "R",
    "FRIDAY": "F",
}

# Extra catalog blocks (Fix 4b). The six solver slots from time_slots.json are
# Tue/Thu 75-minute blocks; these add MWF 50-minute, graduate evening and lab
# blocks. Times are placeholders until the registrar's grid is confirmed.
EXTRA_TIME_SLOTS: List[Tuple[str, str, str, str, Optional[str]]] = [
    # (day_pattern, start, end, pattern_type, level)
    ("MWF", "08:00", "08:50", "MWF_50", "undergraduate"),
    ("MWF", "09:00", "09:50", "MWF_50", "undergraduate"),
    ("MWF", "10:00", "10:50", "MWF_50", "undergraduate"),
    ("MWF", "11:00", "11:50", "MWF_50", "undergraduate"),
    ("MWF", "13:00", "13:50", "MWF_50", "undergraduate"),
    ("TR", "17:30", "18:45", "EVENING_GRAD", "graduate"),
    ("TR", "19:00", "20:15", "EVENING_GRAD", "graduate"),
    ("MW", "14:00", "15:50", "LAB_BLOCK", None),
]

_MODELS_WITH_COUNTS = (
    ("campuses", Campus),
    ("buildings", Building),
    ("rooms", Room),
    ("users", User),
    ("courses", Course),
    ("time_slots", TimeSlot),
    ("semesters", Semester),
    ("preferences", InstructorPreference),
    ("schedules", Schedule),
)


def _load_json(data_dir: str, filename: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_course_code_and_dept(raw_name: str, course_id: int) -> Tuple[str, str]:
    parts = raw_name.strip().split()
    if len(parts) >= 2 and parts[1][0].isdigit():
        dept = parts[0].upper()
        return f"{dept} {parts[1]}", dept
    return f"CS {100 + course_id}", "CS"


def _is_empty(session: Session, model) -> bool:
    return session.exec(select(model).limit(1)).first() is None


def _count(session: Session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


def _reset_tables(session: Session) -> None:
    """Delete children before parents so foreign keys never block the reset."""
    for model in (EditRequest, Schedule, InstructorPreference, Course, Room,
                  Building, Campus, TimeSlot, Semester, User):
        session.execute(delete(model))
    session.commit()


def _seed_campuses_buildings_rooms(session: Session, data_dir: str) -> None:
    if _is_empty(session, Campus):
        for c in _load_json(data_dir, "campuses.json"):
            initials = "".join(w[0].upper() for w in c["name"].split() if w)
            session.add(Campus(id=c["campus_id"], name=c["name"],
                               code=initials[:4] or f"C{c['campus_id']}",
                               address=c.get("address")))
        session.commit()

    if _is_empty(session, Building):
        for b in _load_json(data_dir, "buildings.json"):
            session.add(Building(id=b["building_id"], campus_id=b["campus_id"],
                                 name=b["name"], code=b["code"]))
        session.commit()

    if _is_empty(session, Room):
        for r in _load_json(data_dir, "rooms.json"):
            session.add(Room(id=r["room_id"], building_id=r["building_id"],
                             room_number=r["room_number"], capacity=r["capacity"],
                             room_type=r.get("layout_type", "lecture")))
        session.commit()


def _seed_users_and_courses(session: Session, data_dir: str) -> None:
    if _is_empty(session, User):
        for u in _load_json(data_dir, "users.json"):
            email = u.get("email", f"user{u['user_id']}@umkc.edu")
            session.add(User(id=u["user_id"], username=email.split("@")[0],
                             email=email, full_name=u["name"],
                             role=u.get("role", "instructor"),
                             department=u.get("department", "CS"),
                             priority_score=u.get("priority_points", 100000)))
        session.commit()

    if _is_empty(session, Course):
        used_codes = set()
        for c in _load_json(data_dir, "courses.json"):
            code, dept = _extract_course_code_and_dept(c["course_name"], c["course_id"])
            if code in used_codes:  # course_code is UNIQUE (Fix 2)
                code = f"{code}-{c['course_id']}"
            used_codes.add(code)
            session.add(Course(id=c["course_id"], course_code=code,
                               course_name=c["course_name"], department=dept,
                               credits=c.get("credits", 3),
                               expected_enrollment=c.get("expected_enrollment", 30),
                               requires_lab=c.get("required_layout") == "lab"))
        session.commit()


def _seed_time_slots(session: Session, raw_slots: List[Dict[str, Any]]) -> None:
    if not _is_empty(session, TimeSlot):
        return
    for s in raw_slots:
        label = f"{s['start_time']}-{s['end_time']}"
        session.add(TimeSlot(id=s["slot_id"], day_pattern=s.get("day_pattern", "TR"),
                             start_time=s["start_time"], end_time=s["end_time"],
                             slot_label=label, pattern_type="TR_75", level=None))
    next_id = max([s["slot_id"] for s in raw_slots], default=0) + 1
    for offset, (days, start, end, ptype, level) in enumerate(EXTRA_TIME_SLOTS):
        session.add(TimeSlot(id=next_id + offset, day_pattern=days, start_time=start,
                             end_time=end, slot_label=f"{days} {start}-{end}",
                             pattern_type=ptype, level=level))
    session.commit()


def _seed_semesters(session: Session, data_dir: str) -> None:
    if not _is_empty(session, Semester):
        return
    for sem in _load_json(data_dir, "semesters.json"):
        sid = sem["semester_id"]
        session.add(Semester(id=sem.get("id", sid), semester_id=sid, name=sem["name"],
                             start_date=sem["start_date"], end_date=sem["end_date"],
                             is_active=bool(sem.get("is_active", False))))
    session.commit()


def _seed_preferences(session: Session, data_dir: str, slot_labels: Dict[int, str]) -> None:
    if not _is_empty(session, InstructorPreference):
        return
    room_map = {r["room_id"]: r["room_number"] for r in _load_json(data_dir, "rooms.json")}
    for p in _load_json(data_dir, "instructor_preferences.json"):
        days = [DAY_NAME_TO_CODE.get(str(d).upper(), str(d)) for d in p.get("preferred_days", [])]
        slots = [slot_labels.get(s, str(s)) if isinstance(s, int) else str(s)
                 for s in p.get("preferred_slots", [])]
        rooms = [room_map[p["preferred_room_id"]]] if p.get("preferred_room_id") in room_map else []
        session.add(InstructorPreference(
            id=p["id"], user_id=p["instructor_id"], semester_id=p.get("semester_id", 1),
            course_id=p.get("course_id"), preferred_days=days, preferred_slots=slots,
            preferred_rooms=rooms, preference_rank=1))
    session.commit()


def _seed_schedules(session: Session, data_dir: str) -> None:
    if not _is_empty(session, Schedule):
        return
    for sem_idx in range(1, 7):
        for row in _load_json(data_dir, f"schedules_sem{sem_idx}.json"):
            session.add(Schedule(semester_id=row.get("semester_id", sem_idx),
                                 course_id=row["course_id"], user_id=row["instructor_id"],
                                 room_id=row["room_id"], time_slot_id=row["slot_id"],
                                 status=row.get("status", "confirmed")))
    session.commit()


def seed_database(
    session: Optional[Session] = None,
    data_dir: str = DEFAULT_DATA_DIR,
    force_reset: bool = False,
) -> Dict[str, int]:
    """
    Seeds SQLite from backend/data/umkc/*.json (AC 1.1).
    Idempotent (AC 1.2): a table that already has rows is left untouched, so
    calling this repeatedly never duplicates records unless force_reset=True.
    """
    owns_session = session is None
    if owns_session:
        init_db()
        session = Session(engine)

    try:
        if force_reset:
            _reset_tables(session)

        raw_slots = _load_json(data_dir, "time_slots.json")
        slot_labels = {s["slot_id"]: f"{s['start_time']}-{s['end_time']}" for s in raw_slots}

        _seed_campuses_buildings_rooms(session, data_dir)
        _seed_users_and_courses(session, data_dir)
        _seed_time_slots(session, raw_slots)
        _seed_semesters(session, data_dir)
        _seed_preferences(session, data_dir, slot_labels)
        _seed_schedules(session, data_dir)

        return {name: _count(session, model) for name, model in _MODELS_WITH_COUNTS}
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    print("Database seeded successfully:", seed_database())
