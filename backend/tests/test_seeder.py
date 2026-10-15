from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.seeder import EXTRA_TIME_SLOTS, seed_database
from app.models.entities import Course, InstructorPreference, Room, TimeSlot

EXPECTED_SLOTS = 6 + len(EXTRA_TIME_SLOTS)


def test_seed_database_counts(session: Session):
    """AC 1.1: Exact UMKC entity counts after seeding an empty database."""
    summary = seed_database(session=session)
    assert summary["campuses"] == 2
    assert summary["buildings"] == 5
    assert summary["rooms"] == 12
    assert summary["users"] == 20
    assert summary["courses"] == 40
    assert summary["time_slots"] == EXPECTED_SLOTS
    assert summary["semesters"] == 6
    assert summary["preferences"] > 0
    assert summary["schedules"] == 240  # 40 courses * 6 semesters


def test_seed_database_idempotency(session: Session):
    """AC 1.2: A second run must not duplicate any record."""
    first = seed_database(session=session)
    second = seed_database(session=session)
    assert first == second


def test_seed_database_force_reset(session: Session):
    """force_reset rebuilds the catalog without foreign-key errors."""
    first = seed_database(session=session)
    assert seed_database(session=session, force_reset=True) == first


def test_seeded_catalog_contains_ac_5_1_slot_and_unique_codes(session: Session):
    """The MWF 09:00-09:50 block exists (AC 5.1) and course codes are unique."""
    seed_database(session=session)
    labels = {f"{s.start_time}-{s.end_time}" for s in session.exec(select(TimeSlot)).all()}
    assert "09:00-09:50" in labels
    codes = [c.course_code for c in session.exec(select(Course)).all()]
    assert len(codes) == len(set(codes))


def test_seeded_preferences_use_canonical_values(session: Session):
    """Day names become codes and slot ids become catalog labels."""
    seed_database(session=session)
    allowed_days = set("MTWRF")
    slot_labels = {f"{s.start_time}-{s.end_time}" for s in session.exec(select(TimeSlot)).all()}
    for pref in session.exec(select(InstructorPreference)).all():
        assert set(pref.preferred_days or []) <= allowed_days
        assert set(pref.preferred_slots or []) <= slot_labels
    assert {r.room_type for r in session.exec(select(Room)).all()} <= {
        "lecture", "lab", "seminar", "auditorium"
    }


def test_admin_seed_endpoint(client: TestClient):
    """POST /api/v1/admin/seed returns 200 with the expected counts."""
    response = client.post("/api/v1/admin/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "seeded"
    assert data["users"] == 20
    assert data["courses"] == 40
    assert data["rooms"] == 12
    assert data["time_slots"] == EXPECTED_SLOTS
    assert data["semesters"] == 6

    # Calling it again is a no-op (AC 1.2)
    assert client.post("/api/v1/admin/seed").json() == data
