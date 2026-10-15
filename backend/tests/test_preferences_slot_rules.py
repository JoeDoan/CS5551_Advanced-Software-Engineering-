from app.core.seeder import seed_database
from app.models.entities import Course, User


def _post(client, session, **overrides):
    instructor = session.get(User, 1)
    payload = {"user_id": instructor.id, "semester_id": 1, "preferred_days": ["MWF"]}
    payload.update(overrides)
    return client.post("/api/v1/preferences", json=payload)


def test_unknown_slot_id_returns_404_and_bad_label_returns_422(client, session):
    """AC 5.5: unknown slot id -> 404; label matching no catalog slot -> 422 listing valid ones."""
    seed_database(session=session)

    assert _post(client, session, preferred_slot_ids=[9999]).status_code == 404

    for bad in ("9-10", "13:00-14:15x"):
        resp = _post(client, session, preferred_slots=[bad])
        assert resp.status_code == 422
        assert "09:00-09:50" in resp.json()["detail"]


def test_slot_string_resolves_to_id_and_label(client, session):
    """AC 5.14: '09:00-09:50' resolves to the catalog slot; response has ids and labels."""
    seed_database(session=session)

    resp = _post(client, session, preferred_slots=["09:00-09:50"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["preferred_slots"] == ["09:00-09:50"]
    assert len(data["preferred_slot_ids"]) == 1

    by_id = _post(client, session, preferred_slot_ids=data["preferred_slot_ids"])
    assert by_id.json()["preferred_slots"] == ["09:00-09:50"]


def test_graduate_slot_rejected_for_undergraduate_course(client, session):
    """AC 5.13: graduate-only slot + course number < 5000 -> 422; no-level slot is fine."""
    seed_database(session=session)
    undergrad = session.get(Course, 1)  # CS 101
    assert undergrad.course_code.endswith("101")

    resp = _post(client, session, course_id=undergrad.id, preferred_slots=["17:30-18:45"])
    assert resp.status_code == 422
    assert "graduate-only" in resp.json()["detail"]

    ok = _post(client, session, course_id=undergrad.id, preferred_slots=["14:00-15:50"])
    assert ok.status_code in (200, 201)  # seeded data may already hold this pair (upsert)
