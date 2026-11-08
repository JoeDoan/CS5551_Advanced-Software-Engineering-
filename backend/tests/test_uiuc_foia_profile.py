import csv
import glob
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session, select

from app.core.config import settings
from app.core.seeder import seed_database
from app.models.entities import (
    Course,
    EnrollmentObservation,
    InstructorPreference,
    Room,
    Schedule,
    Semester,
    TimeSlot,
    User,
)
from app.services import solver_service
from app.solver.data_loader import DataLoader
from scripts.build_uiuc_foia_dataset import DEFAULT_OUTPUT_DIR, build_dataset

FORBIDDEN_GRADE_KEYS = frozenset(
    {
        "a+",
        "a",
        "a-",
        "b+",
        "b",
        "b-",
        "c+",
        "c",
        "c-",
        "d+",
        "d",
        "d-",
        "f",
        "w",
        "gpa",
    }
)

EXPECTED_STEM_DEPTS = {"CS", "ECE", "MATH", "STAT", "CHEM", "PHYS", "BIOE"}
EXPECTED_LAB_CODES = {"CS 461", "ECE 206", "ECE 311", "CHEM 315", "BIOE 202"}


def _collect_json_keys(node: Any, out: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            out.add(str(key).strip().lower())
            _collect_json_keys(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_json_keys(item, out)


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_uiuc_foia_zero_gpa_columns_and_offline_determinism(tmp_path: Path):
    uiuc_dir = Path(DEFAULT_OUTPUT_DIR)
    raw_dir = uiuc_dir / "raw"
    csv_files = sorted(raw_dir.glob("*.csv"))
    assert len(csv_files) == 2

    for csv_path in csv_files:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
        lowered = {h.strip().lower() for h in headers}
        assert lowered.isdisjoint(FORBIDDEN_GRADE_KEYS)

    json_files = sorted(uiuc_dir.glob("*.json"))
    assert len(json_files) == 18
    for json_path in json_files:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        keys: set[str] = set()
        _collect_json_keys(payload, keys)
        assert keys.isdisjoint(FORBIDDEN_GRADE_KEYS)

    shutil.copytree(raw_dir, tmp_path / "raw")
    summary = build_dataset(output_dir=str(tmp_path))
    assert summary["courses"] == 40
    assert summary["users"] == 20
    assert summary["rooms"] == 16
    assert summary["semesters"] == 22
    assert summary["enrollment_history"] == 800

    rebuilt_jsons = sorted(Path(p).name for p in glob.glob(str(tmp_path / "*.json")))
    committed_jsons = sorted(p.name for p in json_files)
    assert rebuilt_jsons == committed_jsons
    for filename in committed_jsons:
        if filename.startswith("schedule_"):
            rebuilt_sched = json.loads((tmp_path / filename).read_text(encoding="utf-8"))
            committed_sched = json.loads((uiuc_dir / filename).read_text(encoding="utf-8"))
            assert len(rebuilt_sched) == len(committed_sched)
        else:
            assert _sha256_bytes(tmp_path / filename) == _sha256_bytes(uiuc_dir / filename)


def test_uiuc_foia_seeding_counts_faculty_and_demo_accounts(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    assert settings.data_profile == "uiuc_foia"
    assert settings.DATA_PROFILE == "uiuc_foia"

    summary = seed_database(session=session)
    assert summary["courses"] == 40
    assert summary["users"] == 20
    assert summary["rooms"] == 16
    assert summary["semesters"] == 22
    assert summary["enrollment_observations"] == 800

    courses = session.exec(select(Course)).all()
    assert len(courses) == 40
    assert {c.department for c in courses} == EXPECTED_STEM_DEPTS

    users = session.exec(select(User).order_by(User.id)).all()
    assert len(users) == 20
    assert all(u.email.endswith("@illinois.edu") for u in users)
    assert users[0].id == 1
    assert users[0].full_name == "Dr. Hyoeun Lee"
    assert users[0].email == "leeh@illinois.edu"
    assert users[0].department == "STAT"

    rooms = session.exec(select(Room)).all()
    assert len(rooms) == 16
    assert sum(1 for r in rooms if r.room_type == "lecture") == 12
    assert sum(1 for r in rooms if r.room_type == "lab") == 4

    semesters = session.exec(select(Semester)).all()
    expected_sem_ids = {1, 2, 3, 4, 5, 6} | set(range(101, 117))
    assert {s.semester_id for s in semesters} == expected_sem_ids
    active_sems = [s for s in semesters if s.is_active]
    assert len(active_sems) == 1
    assert active_sems[0].semester_id == 5
    assert active_sems[0].name == "Fall 2026"

    observations = session.exec(select(EnrollmentObservation)).all()
    assert len(observations) == 800
    assert {obs.source for obs in observations} == {"uiuc_foia_registrar"}
    assert all(obs.semester_id not in (5, 6) for obs in observations)

    demo_resp = client.get("/api/v1/auth/demo-accounts")
    assert demo_resp.status_code == 200
    demo_accounts = demo_resp.json()
    faculty_demo = next(a for a in demo_accounts if a["role"] == "instructor")
    assert faculty_demo["full_name"] == "Dr. Hyoeun Lee"
    assert faculty_demo["email"] == "leeh@illinois.edu"
    assert faculty_demo["linked_user_id"] == 1


def test_uiuc_foia_causal_two_year_preferences_and_empty_subset(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    loader = DataLoader()
    sem4_raw = [
        p for p in loader.instructor_preferences if p.get("semester_id") == 4
    ]
    assert len(sem4_raw) == 40

    with_pref = []
    without_pref = []
    for pref in sem4_raw:
        resolved = loader.get_resolved_preference(
            pref["instructor_id"],
            course_id=pref["course_id"],
            semester_id=4,
        )
        if resolved["has_preferences"]:
            with_pref.append(pref)
        else:
            without_pref.append(pref)

    assert len(with_pref) > 0
    assert len(without_pref) > 0
    assert len(with_pref) + len(without_pref) == 40

    lee_stat400 = loader.get_resolved_preference(1, course_id=1, semester_id=4)
    assert lee_stat400["has_preferences"] is False
    assert lee_stat400["days"] == set()
    assert lee_stat400["slots"] == set()
    assert lee_stat400["raw"]["preferred_days"] == []
    assert lee_stat400["raw"]["preferred_slots"] == []

    lee_stat429 = loader.get_resolved_preference(1, course_id=2, semester_id=4)
    assert lee_stat429["has_preferences"] is True
    assert len(lee_stat429["days"]) > 0
    assert len(lee_stat429["slots"]) > 0

    db_sem4_prefs = session.exec(
        select(InstructorPreference).where(InstructorPreference.semester_id == 4)
    ).all()
    assert len(db_sem4_prefs) == 40
    assert sum(1 for p in db_sem4_prefs if p.preferred_days and p.preferred_slots) == (
        len(with_pref)
    )
    assert sum(
        1 for p in db_sem4_prefs if not p.preferred_days and not p.preferred_slots
    ) == len(without_pref)

    heldout_path = os.path.join(
        DEFAULT_OUTPUT_DIR, "heldout_spring2026_ground_truth.json"
    )
    with open(heldout_path, "r", encoding="utf-8") as handle:
        heldout = json.load(handle)
    assert heldout["heldout_semester_id"] == 4
    assert heldout["heldout_semester_name"] == "Spring 2026"
    assert len(heldout["courses"]) == 40
    assert sum(1 for c in heldout["courses"] if c["has_2yr_preference"]) == len(
        with_pref
    )
    assert sum(1 for c in heldout["courses"] if not c["has_2yr_preference"]) == len(
        without_pref
    )


def test_uiuc_foia_cpsat_solver_runs_cleanly_on_sem5_and_sem6(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    rooms_by_id = {r.id: r for r in session.exec(select(Room)).all()}
    courses_by_id = {c.id: c for c in session.exec(select(Course)).all()}

    for target_sem_id in (5, 6):
        result = solver_service.run_solver_for_semester(
            session=session, semester_id=target_sem_id
        )
        assert result["status"] in ("OPTIMAL", "FEASIBLE")
        assert result["scheduled_count"] == 40

        slots_by_id = {s.id: s for s in session.exec(select(TimeSlot)).all()}
        rows = session.exec(
            select(Schedule).where(Schedule.semester_id == target_sem_id)
        ).all()
        assert len(rows) == 40
        assert len({row.course_id for row in rows}) == 40

        room_occupied: set[tuple[int, str, str, str]] = set()
        inst_occupied: set[tuple[int, str, str, str]] = set()

        for row in rows:
            room = rooms_by_id[row.room_id]
            course = courses_by_id[row.course_id]
            slot = slots_by_id[row.time_slot_id]

            assert room.capacity >= course.expected_enrollment
            if course.course_code in EXPECTED_LAB_CODES:
                assert room.room_type == "lab"

            assert len(slot.day_pattern) >= 2
            for day_ch in slot.day_pattern:
                rk = (row.room_id, day_ch, slot.start_time, slot.end_time)
                ik = (row.user_id, day_ch, slot.start_time, slot.end_time)
                assert rk not in room_occupied
                assert ik not in inst_occupied
                room_occupied.add(rk)
                inst_occupied.add(ik)


def test_uiuc_foia_hyoeun_lee_evening_preferences_reschedule_courses(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    pref_resp = client.post(
        "/api/v1/preferences",
        json={
            "user_id": 1,
            "semester_id": 5,
            "course_id": None,
            "preferred_days": ["M", "R"],
            "preferred_slots": ["17:30-18:45", "19:00-20:15"],
            "preferred_rooms": [],
        },
    )
    assert pref_resp.status_code in (200, 201)

    solver_resp = client.post("/api/v1/solver/run", json={"semester_id": 5})
    assert solver_resp.status_code == 200
    assert solver_resp.json()["status"] in ("OPTIMAL", "FEASIBLE")

    sched_resp = client.get("/api/v1/schedules", params={"semester_id": 5})
    assert sched_resp.status_code == 200
    all_sections = sched_resp.json()
    assert len(all_sections) == 40

    lee_sections = [s for s in all_sections if s["user_id"] == 1]
    assert len(lee_sections) == 2
    assert {s["instructor_name"] for s in lee_sections} == {"Dr. Hyoeun Lee"}
    assert {s["course_code"] for s in lee_sections} == {"STAT 400", "STAT 429"}
    assert {s["day_pattern"] for s in lee_sections} == {"MR"}
    assert {(s["start_time"], s["end_time"]) for s in lee_sections} == {
        ("17:30", "18:45"),
        ("19:00", "20:15"),
    }

    non_requesting_evening = [
        s
        for s in all_sections
        if s["user_id"] != 1
        and (s["start_time"], s["end_time"])
        in {("17:30", "18:45"), ("19:00", "20:15")}
    ]
    assert non_requesting_evening == []


def test_uiuc_foia_whatif_simulation_with_forecast_on_spring_2027(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    resp = client.post(
        "/api/v1/scenarios/simulate",
        json={
            "semester_id": 6,
            "use_forecast": True,
            "time_limit_seconds": 8,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["semester_name"] == "Spring 2027"
    assert data["baseline"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["scenario"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["scenario"]["scheduled_courses"] == 40


def test_uiuc_foia_per_course_preferences_schedule_distinct_slots_for_each_course(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    seed_database(session=session)

    lee_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "leeh@illinois.edu", "password": "faculty123"},
    )
    assert lee_login.status_code == 200, lee_login.text
    lee_headers = {"Authorization": f"Bearer {lee_login.json()['access_token']}"}
    lee_uid = lee_login.json()["user"]["linked_user_id"]
    assert lee_uid == 1

    unassigned_cs = session.exec(
        select(Course).where(Course.department == "CS").order_by(Course.id)
    ).first()
    assert unassigned_cs is not None

    unassigned_resp = client.post(
        "/api/v1/preferences",
        headers=lee_headers,
        json={
            "user_id": lee_uid,
            "semester_id": 5,
            "course_id": unassigned_cs.id,
            "preferred_days": ["M", "W"],
            "preferred_slots": ["09:30-10:45"],
            "preferred_rooms": [],
        },
    )
    assert unassigned_resp.status_code == 403
    assert "Course Coordinators" in unassigned_resp.json()["detail"]

    general_resp = client.post(
        "/api/v1/preferences",
        headers=lee_headers,
        json={
            "user_id": lee_uid,
            "semester_id": 5,
            "course_id": None,
            "preferred_days": ["M", "W"],
            "preferred_slots": ["11:00-12:15"],
            "preferred_rooms": [],
        },
    )
    assert general_resp.status_code in (200, 201), general_resp.text
    assert general_resp.json()["preference_rank"] == 1

    stat400_resp = client.post(
        "/api/v1/preferences",
        headers=lee_headers,
        json={
            "user_id": lee_uid,
            "semester_id": 5,
            "course_id": 1,
            "preferred_days": ["M", "W"],
            "preferred_slots": ["09:30-10:45"],
            "preferred_rooms": [],
        },
    )
    assert stat400_resp.status_code in (200, 201), stat400_resp.text
    assert stat400_resp.json()["preference_rank"] == 1

    stat429_resp = client.post(
        "/api/v1/preferences",
        headers=lee_headers,
        json={
            "user_id": lee_uid,
            "semester_id": 5,
            "course_id": 2,
            "preferred_days": ["M", "R"],
            "preferred_slots": ["19:00-20:15"],
            "preferred_rooms": [],
        },
    )
    assert stat429_resp.status_code in (200, 201), stat429_resp.text
    assert stat429_resp.json()["preference_rank"] == 1

    coord_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "coordinator", "password": "coordinator123"},
    )
    assert coord_login.status_code == 200, coord_login.text
    coord_headers = {
        "Authorization": f"Bearer {coord_login.json()['access_token']}"
    }

    solve_resp = client.post(
        "/api/v1/solver/run",
        headers=coord_headers,
        json={"semester_id": 5},
    )
    assert solve_resp.status_code == 200, solve_resp.text
    assert solve_resp.json()["status"] in ("OPTIMAL", "FEASIBLE")

    all_sections = client.get(
        "/api/v1/schedules", params={"semester_id": 5}
    ).json()
    assert len(all_sections) == 40
    lee_by_code = {
        s["course_code"]: s for s in all_sections if s["user_id"] == lee_uid
    }
    assert set(lee_by_code.keys()) == {"STAT 400", "STAT 429"}
    assert lee_by_code["STAT 400"]["day_pattern"] == "MW"
    assert (
        lee_by_code["STAT 400"]["start_time"],
        lee_by_code["STAT 400"]["end_time"],
    ) == ("09:30", "10:45")
    assert lee_by_code["STAT 429"]["day_pattern"] == "MR"
    assert (
        lee_by_code["STAT 429"]["start_time"],
        lee_by_code["STAT 429"]["end_time"],
    ) == ("19:00", "20:15")

    audit = client.get(
        "/api/v1/analytics/conflicts", params={"semester_id": 5}
    ).json()
    assert audit["is_conflict_free"] is True
    assert audit["hard_violation_count"] == 0

    fairness = client.get(
        "/api/v1/analytics/fairness", params={"semester_id": 5}
    ).json()
    lee_fairness = next(
        item for item in fairness["instructors"] if item["user_id"] == lee_uid
    )
    assert lee_fairness["preferred_day_matches"] == 2
    assert lee_fairness["satisfaction_rate"] == 100.0
