import importlib.util
import json
import os

from sqlmodel import select

from app.core.seeder import DEFAULT_DATA_DIR, seed_database
from app.models.entities import EnrollmentObservation
from app.services.forecast_service import MODEL_NAMES

SCRIPT = os.path.join(
    os.path.dirname(DEFAULT_DATA_DIR), "scripts", "generate_enrollment_history.py"
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_enrollment_history", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(client, session):
    seed_database(session=session)
    return client


def test_seed_loads_synthetic_enrollment_history(session):
    summary = seed_database(session=session)
    assert summary["enrollment_observations"] == 200  # 40 courses x semesters 1-5
    rows = session.exec(select(EnrollmentObservation)).all()
    assert {r.source for r in rows} == {"synthetic"}
    assert {r.semester_id for r in rows} == {1, 2, 3, 4, 5}
    assert all(r.enrolled >= 1 for r in rows)


def test_history_file_matches_generator_output():
    """Guards against a stale committed history file."""
    gen = _load_generator()
    with open(os.path.join(DEFAULT_DATA_DIR, "courses.json"), encoding="utf-8") as f:
        courses = json.load(f)
    with open(os.path.join(DEFAULT_DATA_DIR, "enrollment_history.json"), encoding="utf-8") as f:
        committed = json.load(f)
    assert gen.generate(courses) == committed
    assert gen.generate(courses) == gen.generate(courses)  # deterministic


def test_forecast_endpoint_shape_and_honesty_flags(client, session):
    _seed(client, session)
    resp = client.get("/api/v1/forecast/enrollment")
    assert resp.status_code == 200
    data = resp.json()
    meta = data["meta"]
    assert meta["target_semester_id"] == 6
    assert meta["target_semester_name"] == "Spring 2027"
    assert meta["observed_semester_ids"] == [1, 2, 3, 4, 5]
    assert meta["backtest_origins"] == [4, 5]
    assert meta["is_synthetic"] is True
    assert "SYNTHETIC" in meta["note"]
    assert meta["champion_model"] in MODEL_NAMES
    assert set(data["model_metrics"]) == set(MODEL_NAMES)
    assert len(data["courses"]) == 40
    for c in data["courses"]:
        assert len(c["history"]) == 5
        lo80, hi80 = c["interval_80"]
        lo95, hi95 = c["interval_95"]
        assert lo95 <= lo80 <= c["forecast"] <= hi80 <= hi95
        assert set(c["forecasts"]) == set(MODEL_NAMES)


def test_champion_has_lowest_backtest_mae_and_intervals_cover(client, session):
    _seed(client, session)
    data = client.get("/api/v1/forecast/enrollment").json()
    maes = {m: v["mae"] for m, v in data["model_metrics"].items()}
    assert maes[data["meta"]["champion_model"]] == min(maes.values())
    # Calibrate on the earlier origin, test on the last: should be near the 80% target.
    assert data["meta"]["held_out_coverage_80"] >= 0.7
    assert data["meta"]["interval_calibration_n"] == 80


def test_forecast_is_deterministic(client, session):
    _seed(client, session)
    a = client.get("/api/v1/forecast/enrollment").json()
    b = client.get("/api/v1/forecast/enrollment").json()
    assert a == b


def test_only_next_unobserved_semester_is_supported(client, session):
    _seed(client, session)
    assert client.get("/api/v1/forecast/enrollment?semester_id=6").status_code == 200
    assert client.get("/api/v1/forecast/enrollment?semester_id=5").status_code == 422
    assert client.get("/api/v1/forecast/enrollment?semester_id=7").status_code == 422


def test_forecast_404_without_history(client):
    resp = client.get("/api/v1/forecast/enrollment")
    assert resp.status_code == 404
    assert "history" in resp.json()["detail"].lower()


def test_bottlenecks_surface_the_seed_capacity_cliffs(client, session):
    _seed(client, session)
    data = client.get("/api/v1/forecast/bottlenecks").json()
    items = data["items"]
    assert len(items) == 40
    assert sum(data["summary"]["tier_counts"].values()) == 40
    by_code = {i["course_code"]: i for i in items}
    for code in ("BIOL 108", "CHEM 432", "ECE 380"):
        assert by_code[code]["capacity_cliff_pct"] == 7.1
    top = {i["course_code"] for i in data["summary"]["tightest_cliffs"][:3]}
    assert top == {"BIOL 108", "CHEM 432", "ECE 380"}
    # Lab courses are only compatible with lab rooms.
    assert by_code["CHEM 432"]["max_room_capacity"] == 30
    assert by_code["BIOL 108"]["largest_compatible_room"] == "SCB 101"
    for i in items:
        assert 0 < i["overflow_probability"] <= 1
        assert i["risk_tier"] in {"critical", "high", "watch", "ok"}
        if i["risk_tier"] == "ok":
            assert i["remedy"] is None
        else:
            assert i["remedy"]["solver_confirmed"] is False


def test_items_sorted_by_risk_and_seat_bands(client, session):
    _seed(client, session)
    data = client.get("/api/v1/forecast/bottlenecks").json()
    order = {"critical": 0, "high": 1, "watch": 2, "ok": 3}
    ranks = [order[i["risk_tier"]] for i in data["items"]]
    assert ranks == sorted(ranks)
    bands = {b["min_seats"]: b for b in data["summary"]["seat_band_pressure"]}
    assert bands[100]["rooms_available"] == 2  # SCB 101 and RH 204
    assert bands[60]["rooms_available"] == 4


def test_forecast_access_for_both_roles_but_not_anonymous(client, session, monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    seed_database(session=session)
    assert client.get("/api/v1/forecast/enrollment").status_code == 401
    assert client.get("/api/v1/forecast/bottlenecks").status_code == 401
    for identifier, password in (
        ("coordinator@umkc.edu", "coordinator123"),
        ("leeyu@umkc.edu", "faculty123"),
    ):
        login = client.post(
            "/api/v1/auth/login", json={"identifier": identifier, "password": password}
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.get("/api/v1/forecast/enrollment", headers=headers).status_code == 200
        assert client.get("/api/v1/forecast/bottlenecks", headers=headers).status_code == 200
