import logging
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

import app.core.startup as startup
from app.core.startup import (
    StartupReport,
    detect_schema_drift,
    prepare_database,
    rebuild_sqlite,
    start_warmup,
)
from app.main import app


def _stale_engine(tmp_path):
    """A SQLite file shaped like an older release: time_slots lacks pattern_type and level."""
    path = tmp_path / "stale.db"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE time_slots (id INTEGER PRIMARY KEY, day_pattern TEXT, "
        "start_time TEXT, end_time TEXT, slot_label TEXT)"
    )
    con.execute("INSERT INTO time_slots VALUES (1, 'TR', '08:00', '09:15', 'old row')")
    con.commit()
    con.close()
    return create_engine(f"sqlite:///{path}"), path


def _fresh_engine(tmp_path):
    return create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")


def test_fresh_database_has_no_drift(tmp_path):
    engine = _fresh_engine(tmp_path)
    report = prepare_database(engine, auto_seed=False, rebuild_stale=False)
    assert report.ok and report.schema_issues == []


def test_drift_names_the_missing_columns(tmp_path):
    engine, _ = _stale_engine(tmp_path)
    issues = detect_schema_drift(engine)
    assert issues == ["table 'time_slots' is missing column(s): pattern_type, level"]


def test_stale_database_is_reported_loudly_and_never_seeded(tmp_path, caplog):
    engine, path = _stale_engine(tmp_path)
    seeded = []
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        report = prepare_database(
            engine, auto_seed=True, rebuild_stale=False, seed=lambda: seeded.append(1)
        )
    assert not report.ok and report.seeded is False and seeded == []
    assert report.rebuilt_backup is None
    text = caplog.text
    assert "DATABASE SCHEMA IS OUT OF DATE" in text
    assert "pattern_type" in text and "REBUILD_STALE_DB=true" in text
    # the file was left exactly as it was
    assert [c["name"] for c in inspect(engine).get_columns("time_slots")] == [
        "id", "day_pattern", "start_time", "end_time", "slot_label",
    ]
    assert path.exists() and not list(tmp_path.glob("*.bak"))


def test_rebuild_keeps_a_backup_and_then_seeds(tmp_path):
    engine, path = _stale_engine(tmp_path)
    seeded = []
    report = prepare_database(
        engine, auto_seed=True, rebuild_stale=True, seed=lambda: seeded.append(1)
    )
    assert report.ok and report.seeded and seeded == [1]
    assert report.rebuilt_backup and report.rebuilt_backup.startswith(str(path))
    backups = list(tmp_path.glob("stale.db.stale-*.bak"))
    assert len(backups) == 1
    old = sqlite3.connect(backups[0]).execute("SELECT slot_label FROM time_slots").fetchall()
    assert old == [("old row",)]  # the previous data survives in the backup
    assert detect_schema_drift(engine) == []


def test_a_failed_rebuild_is_reported_not_raised(tmp_path, monkeypatch):
    engine, _ = _stale_engine(tmp_path)

    def locked(_engine):
        raise PermissionError("file is in use by another process")

    monkeypatch.setattr(startup, "rebuild_sqlite", locked)
    report = prepare_database(engine, auto_seed=True, rebuild_stale=True, seed=lambda: None)
    assert not report.ok and report.seeded is False and report.schema_issues


def test_rebuild_only_touches_sqlite_files(tmp_path):
    fake_pg = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    assert rebuild_sqlite(fake_pg) is None
    memory = create_engine("sqlite://")
    assert rebuild_sqlite(memory) is None
    missing = create_engine(f"sqlite:///{tmp_path / 'nope.db'}")
    assert rebuild_sqlite(missing) is None


def test_seed_failures_are_recorded_and_logged(tmp_path, caplog):
    engine = _fresh_engine(tmp_path)

    def boom():
        raise RuntimeError("bad data file")

    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        report = prepare_database(engine, auto_seed=True, rebuild_stale=False, seed=boom)
    assert not report.ok and report.seed_error == "RuntimeError: bad data file"
    assert "Auto-seed FAILED" in caplog.text


def test_auto_seed_off_skips_seeding(tmp_path):
    engine = _fresh_engine(tmp_path)
    calls = []
    report = prepare_database(engine, auto_seed=False, rebuild_stale=False, seed=lambda: calls.append(1))
    assert report.ok and report.seeded is False and calls == []


def test_health_reports_a_degraded_database():
    client = TestClient(app)
    previous = getattr(app.state, "startup_report", None)
    try:
        app.state.startup_report = StartupReport(
            schema_issues=["table 'time_slots' is missing column(s): pattern_type"]
        )
        body = client.get("/api/v1/health").json()
        assert body["status"] == "degraded"
        assert body["database"]["schema_ok"] is False
        assert "pattern_type" in body["database"]["issues"][0]

        app.state.startup_report = StartupReport(seeded=True)
        body = client.get("/api/v1/health").json()
        assert body["status"] == "healthy" and body["database"]["schema_ok"] is True
    finally:
        app.state.startup_report = previous
        if previous is None:
            del app.state.startup_report


def test_warmup_solves_the_baseline_and_primes_claude(monkeypatch):
    import app.services.copilot_service as copilot
    import app.services.scenario_service as scenario

    calls = []
    monkeypatch.setattr(scenario, "simulate_scenario", lambda s, spec: calls.append("baseline"))
    monkeypatch.setattr(copilot, "llm_enabled", lambda: True)
    monkeypatch.setattr(copilot, "load_vocabulary", lambda s: "vocab")
    monkeypatch.setattr(copilot, "parse_prompt", lambda p, v: calls.append("claude"))
    start_warmup(create_engine("sqlite://")).join(timeout=10)
    assert calls == ["baseline", "claude"]


def test_warmup_failures_never_propagate(monkeypatch, caplog):
    import app.services.scenario_service as scenario

    def boom(*_a, **_k):
        raise RuntimeError("no data")

    monkeypatch.setattr(scenario, "simulate_scenario", boom)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        thread = start_warmup(create_engine("sqlite://"))
        thread.join(timeout=10)
    assert not thread.is_alive()
    assert "Warm-up skipped" in caplog.text


@pytest.mark.parametrize("flag", ["REBUILD_STALE_DB", "DEMO_WARMUP"])
def test_startup_flags_default_to_off(monkeypatch, flag):
    from app.main import _flag

    monkeypatch.delenv(flag, raising=False)
    assert _flag(flag) is False
    monkeypatch.setenv(flag, "true")
    assert _flag(flag) is True
