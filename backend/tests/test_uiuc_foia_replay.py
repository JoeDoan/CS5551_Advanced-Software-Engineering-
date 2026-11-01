import time

from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session, select

from app.core.seeder import seed_database
from app.models.entities import Room
from app.services import copilot_service

EXPECTED_LAB_CODES = {"CS 461", "ECE 206", "ECE 311", "CHEM 315", "BIOE 202"}


def test_uiuc_foia_20_term_chronological_enrollment_forecast(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    resp = client.get("/api/v1/forecast/enrollment")
    assert resp.status_code == 200
    body = resp.json()
    meta = body["meta"]

    assert meta["is_synthetic"] is False
    assert meta["note"] is None
    assert meta["data_source"] == "uiuc_foia_registrar"
    assert meta["target_semester_id"] == 5
    assert meta["target_semester_name"] == "Fall 2026"
    assert meta["observed_semester_ids"] == [
        *range(101, 117),
        1,
        2,
        3,
        4,
    ]
    assert len(meta["observed_semester_ids"]) == 20
    assert meta["observed_semester_ids"][0] == 101
    assert meta["observed_semester_ids"][-1] == 4
    assert len(meta["backtest_origins"]) == 16
    assert meta["interval_calibration_n"] == 640

    courses = body["courses"]
    assert len(courses) == 40
    for course in courses:
        assert len(course["history"]) == 20
        assert course["history"][0]["semester_name"] == "Fall 2016"
        assert course["history"][-1]["semester_name"] == "Spring 2026"
        assert all(pt["semester_id"] not in (5, 6) for pt in course["history"])

    resp_sem6 = client.get(
        "/api/v1/forecast/enrollment", params={"semester_id": 6}
    )
    assert resp_sem6.status_code == 200
    meta_sem6 = resp_sem6.json()["meta"]
    assert meta_sem6["target_semester_id"] == 6
    assert meta_sem6["target_semester_name"] == "Spring 2027"
    assert len(meta_sem6["observed_semester_ids"]) == 20

    resp_sem4 = client.get(
        "/api/v1/forecast/enrollment", params={"semester_id": 4}
    )
    assert resp_sem4.status_code == 422


def test_empirical_benchmark_returns_404_on_umkc_profile(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "umkc")
    resp = client.get("/api/v1/forecast/empirical-benchmark")
    assert resp.status_code == 404
    assert "Empirical benchmark ground truth" in resp.json()["detail"]


def test_empirical_benchmark_two_stage_non_circular_evaluation_and_cache(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
    client: TestClient,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    resp1 = client.get("/api/v1/forecast/empirical-benchmark")
    assert resp1.status_code == 200
    data = resp1.json()

    t0 = time.perf_counter()
    resp2 = client.get("/api/v1/forecast/empirical-benchmark")
    cached_ms = (time.perf_counter() - t0) * 1000.0
    assert resp2.status_code == 200
    assert resp2.json() == data
    assert cached_ms < 50.0

    assert data["dataset_source"] == (
        "UIUC FOIA Registrar & Course Explorer 2016-2026"
    )
    assert data["heldout_semester_id"] == 4
    assert data["heldout_semester_name"] == "Spring 2026"
    assert data["observed_semesters_count"] == 19
    assert data["evaluated_courses_count"] == 40
    assert data["courses_with_2yr_habit_pref"] == 25
    assert data["courses_without_pref"] == 15

    fb = data["forecast_benchmark"]
    assert fb["champion_model"] in (
        "seasonal_naive",
        "damped_trend",
        "pooled_ridge",
    )
    assert fb["champion_mae"] < fb["last_term_copy_naive_mae"]
    assert fb["mae_reduction_vs_last_term_pct"] > 0.0
    assert 0.70 <= fb["empirical_coverage_80"] <= 1.0
    assert 0.85 <= fb["empirical_coverage_95"] <= 1.0

    sb = data["schedule_benchmark"]
    assert sb["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert sb["hard_conflicts"] == 0
    assert (
        sb["overflow_courses_conformal_80_sizing"]
        < sb["overflow_courses_point_forecast_sizing"]
    )
    assert (
        sb["overflow_courses_conformal_80_sizing"]
        < sb["overflow_courses_last_term_sizing"]
    )
    assert (
        sb["optisched_seat_utilization_pct"]
        > sb["uiuc_actual_seat_utilization_pct"]
    )
    assert (
        sb["optisched_empty_seat_waste_pct"]
        < sb["uiuc_empty_seat_waste_pct"]
    )
    assert (
        sb["optisched_midday_concentration_pct"]
        < sb["uiuc_midday_concentration_pct"]
    )
    assert sb["habit_continuity_on_pref_courses_pct"] >= 80.0

    rows = data["course_comparisons"]
    assert len(rows) == 40
    assert sum(1 for r in rows if r["has_2yr_preference"]) == 25
    assert sum(1 for r in rows if not r["has_2yr_preference"]) == 15

    lab_rooms = {
        r.room_number
        for r in session.exec(select(Room)).all()
        if r.room_type == "lab"
    }
    for row in rows:
        assert row["optisched_room"]
        assert row["optisched_room_capacity"] > 0
        assert row["optisched_slot"]
        assert row["uiuc_actual_room"]
        assert row["uiuc_actual_room_capacity"] > 0
        assert row["uiuc_actual_slot"]
        if row["course_code"] in EXPECTED_LAB_CODES:
            assert row["optisched_room"] in lab_rooms


def test_copilot_parses_bioe_growth_lee_buyout_and_spring_2027_without_warnings(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
):
    monkeypatch.setenv("DATA_PROFILE", "uiuc_foia")
    seed_database(session=session)

    vocab = copilot_service.load_vocabulary(session)
    assert "BIOE" in vocab.departments
    assert vocab.target_semester == "Spring 2027"

    parsed = copilot_service.parse_prompt(
        "What if BIOE enrollment grows 20% and Dr. Lee takes a 1-course buyout "
        "in Spring 2027?",
        vocab,
        use_llm=False,
    )
    assert parsed.understood is True
    assert parsed.warnings == []
    assert [
        (g.department, g.pct) for g in parsed.spec.enrollment_growth
    ] == [("BIOE", 20.0)]
    assert [b.instructor for b in parsed.spec.buyouts] == ["Dr. Hyoeun Lee"]

    off_term = copilot_service.parse_prompt(
        "What if biomedical engineering grows 15% in Fall 2028?",
        vocab,
        use_llm=False,
    )
    assert [
        (g.department, g.pct) for g in off_term.spec.enrollment_growth
    ] == [("BIOE", 15.0)]
    assert any("Only Spring 2027 is simulated" in w for w in off_term.warnings)
