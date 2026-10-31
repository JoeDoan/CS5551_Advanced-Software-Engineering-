import glob
import hashlib
import os

import pytest
from sqlmodel import func, select

import app.services.scenario_service as scenario_service
from app.core.seeder import DEFAULT_DATA_DIR, seed_database
from app.models.entities import InstructorPreference, Schedule, User

URL = "/api/v1/scenarios/simulate"
LEE = "Dr. Yugyung Lee"
BUYOUT = [{"instructor": LEE, "max_courses": 1}]


@pytest.fixture(autouse=True)
def _fast_baseline(monkeypatch):
    # Baseline is cached across tests (same seeded data), so this is solved once.
    monkeypatch.setattr(scenario_service, "BASELINE_TIME_LIMIT_SECONDS", 30.0)


def _post(client, **spec):
    spec.setdefault("semester_id", 6)
    spec.setdefault("time_limit_seconds", 8)
    return client.post(URL, json=spec)


def _data_digest():
    h = hashlib.sha256()
    backend = os.path.dirname(os.path.dirname(DEFAULT_DATA_DIR))
    files = sorted(glob.glob(os.path.join(DEFAULT_DATA_DIR, "*.json")))
    files.append(os.path.join(backend, "data", "scripts", "instructor_profiles.json"))
    for f in files:
        with open(f, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()


def test_noop_scenario_reproduces_the_baseline(client, session):
    seed_database(session=session)
    resp = _post(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["semester_name"] == "Spring 2027"
    assert data["baseline"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["scenario"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["baseline"]["scheduled_courses"] == 40
    assert data["diff"]["changed_courses"] == []
    assert abs(data["diff"]["satisfaction_delta_pct"]) < 0.01
    assert any("Dry run" in n for n in data["notes"])


def test_buyout_without_coverage_is_provably_infeasible(client, session):
    seed_database(session=session)
    data = _post(client, buyouts=BUYOUT, coverage_strategy="none").json()
    assert data["scenario"]["status"] == "INFEASIBLE"
    diag = " ".join(data["scenario"]["diagnosis"])
    assert "40 courses" in diag and "39" in diag
    assert data["diff"]["changed_courses"] == []


def test_overload_strategy_moves_one_course_to_a_colleague(client, session):
    seed_database(session=session)
    data = _post(client, buyouts=BUYOUT, coverage_strategy="overload").json()
    scen = data["scenario"]
    assert scen["status"] in ("OPTIMAL", "FEASIBLE")
    assert scen["scheduled_courses"] == 40
    assert scen["instructor_loads"][LEE] == 1
    assert data["diff"]["released"] == [LEE]
    assert len(data["diff"]["absorbers"]) == 1
    absorber = data["diff"]["absorbers"][0]
    assert scen["instructor_loads"][absorber] == 3
    assert len(data["diff"]["changed_courses"]) == 1  # minimal policy: only the forced move
    assert data["diff"]["satisfaction_delta_pct"] <= 0.01  # a buyout never helps here


def test_adjunct_strategy_covers_the_freed_section(client, session):
    seed_database(session=session)
    data = _post(client, buyouts=BUYOUT, coverage_strategy="adjunct").json()
    scen = data["scenario"]
    assert scen["status"] in ("OPTIMAL", "FEASIBLE")
    assert scen["instructor_loads"][LEE] == 1
    assert scen["instructor_loads"][scenario_service.ADJUNCT_NAME] == 1
    assert len(data["diff"]["adjunct_sections"]) == 1
    assert data["diff"]["absorbers"] == []
    moved = data["diff"]["changed_courses"]
    assert [c["course"] for c in moved] == data["diff"]["adjunct_sections"]


def test_reoptimize_policy_may_move_more_courses_than_minimal(client, session):
    """Minimal is a hard guarantee (one forced move); re-optimize only *permits* more.

    Whether the solver finds a rearrangement worth making inside the time limit varies
    from run to run, so this asserts the guaranteed direction, not an exact count.
    """
    seed_database(session=session)
    minimal = _post(client, buyouts=BUYOUT, coverage_strategy="adjunct").json()
    wide = _post(
        client, buyouts=BUYOUT, coverage_strategy="adjunct", change_policy="reoptimize",
        time_limit_seconds=30,
    ).json()
    assert wide["scenario"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(minimal["diff"]["changed_courses"]) == 1
    assert len(wide["diff"]["changed_courses"]) >= len(minimal["diff"]["changed_courses"])
    assert any("reoptimize" in n for n in wide["notes"])
    assert any("'minimal'" in n for n in minimal["notes"])


def test_enrollment_beyond_every_room_is_diagnosed_without_solving(client, session):
    seed_database(session=session)
    data = _post(client, enrollment_growth=[{"department": "BIOL", "pct": 10}]).json()
    assert data["scenario"]["status"] == "INFEASIBLE"
    assert "BIOL 108" in data["scenario"]["diagnosis"][0]
    assert "150" in data["scenario"]["diagnosis"][0]
    shrunk = _post(client, room_capacity_scale=0.5).json()
    assert shrunk["scenario"]["status"] == "INFEASIBLE"


def test_blocked_room_slot_is_respected(client, session):
    seed_database(session=session)
    first = _post(client).json()["baseline"]["assignments"][0]
    block = {"room_number": first["room"], "slot_id": first["slot_id"], "reason": "Incubator"}
    data = _post(client, blocked_room_slots=[block]).json()
    assert data["scenario"]["status"] in ("OPTIMAL", "FEASIBLE")
    used = {(a["room"], a["slot_id"]) for a in data["scenario"]["assignments"]}
    assert (first["room"], first["slot_id"]) not in used
    assert data["diff"]["changed_courses"]  # the displaced course moved


def test_scenarios_never_write_data_or_database(client, session):
    seed_database(session=session)
    files_before = _data_digest()
    sched = session.exec(select(func.count()).select_from(Schedule)).one()
    prefs = session.exec(select(func.count()).select_from(InstructorPreference)).one()
    priorities = sum(u.priority_score for u in session.exec(select(User)).all())
    assert _post(client, buyouts=BUYOUT, coverage_strategy="overload").status_code == 200
    assert _data_digest() == files_before
    assert session.exec(select(func.count()).select_from(Schedule)).one() == sched
    assert session.exec(select(func.count()).select_from(InstructorPreference)).one() == prefs
    assert sum(u.priority_score for u in session.exec(select(User)).all()) == priorities


def test_validation_errors(client, session):
    seed_database(session=session)
    assert _post(client, buyouts=[{"instructor": LEE, "max_courses": 3}]).status_code == 422
    assert _post(client, buyouts=BUYOUT + BUYOUT).status_code == 422
    assert _post(client, time_limit_seconds=500).status_code == 422
    assert _post(client, enrollment_growth=[{"department": "CS", "pct": 500}]).status_code == 422
    assert _post(client, buyouts=[{"instructor": "Dr. Nobody", "max_courses": 1}]).status_code == 422
    assert _post(client, enrollment_growth=[{"department": "ZZZ", "pct": 5}]).status_code == 422
    assert _post(client, semester_id=99).status_code == 404
    # Forecast is only defined for the next unobserved semester.
    assert _post(client, semester_id=5, use_forecast=True).status_code == 422


def test_faculty_scope_redaction_and_auth(client, session, monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    seed_database(session=session)
    assert _post(client, buyouts=BUYOUT).status_code == 401

    login = client.post(
        "/api/v1/auth/login", json={"identifier": "leeyu@umkc.edu", "password": "faculty123"}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    def faculty(**spec):
        spec.setdefault("semester_id", 6)
        spec.setdefault("time_limit_seconds", 8)
        return client.post(URL, json=spec, headers=headers)

    assert faculty().status_code == 403  # no buyout
    assert faculty(buyouts=[{"instructor": "Dr. Praveen Rao", "max_courses": 1}]).status_code == 403
    assert faculty(buyouts=BUYOUT, enrollment_growth=[{"department": "CS", "pct": 5}]).status_code == 403
    assert faculty(buyouts=BUYOUT, room_capacity_scale=0.8).status_code == 403

    ok = faculty(buyouts=BUYOUT, coverage_strategy="overload")
    assert ok.status_code == 200, ok.text
    data = ok.json()
    allowed = {LEE, "Colleague", scenario_service.ADJUNCT_NAME}
    for side in ("baseline", "scenario"):
        for a in data[side]["assignments"]:
            assert set(a["instructors"]) <= allowed
        assert set(data[side]["satisfaction_by_instructor"]) <= {LEE}
        assert set(data[side]["instructor_loads"]) <= {LEE, scenario_service.ADJUNCT_NAME}
    assert data["diff"]["absorbers"] == ["Colleague"]
    for ch in data["diff"]["changed_courses"]:
        assert set(ch["instructors_before"] + ch["instructors_after"]) <= allowed

    coordinator = client.post(
        "/api/v1/auth/login", json={"identifier": "coordinator@umkc.edu", "password": "coordinator123"}
    ).json()["access_token"]
    full = client.post(
        URL,
        json={"semester_id": 6, "buyouts": BUYOUT, "time_limit_seconds": 8},
        headers={"Authorization": f"Bearer {coordinator}"},
    )
    assert full.status_code == 200
    assert "Colleague" not in str(full.json()["diff"]["absorbers"])
