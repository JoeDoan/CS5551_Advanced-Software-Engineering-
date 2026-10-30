from app.models.entities import (
    Building,
    Campus,
    Course,
    Room,
    Schedule,
    Semester,
    TimeSlot,
    User,
)


def _seed_edit_request_fixture(session):
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()

    bldg = Building(campus_id=campus.id, name="Haag Hall", code="HH")
    session.add(bldg)
    session.commit()

    room1 = Room(
        building_id=bldg.id, room_number="HH-101", capacity=50, room_type="lecture"
    )
    room2 = Room(
        building_id=bldg.id, room_number="HH-202", capacity=50, room_type="lecture"
    )
    session.add_all([room1, room2])

    inst1 = User(
        username="tony_inst",
        email="inst1@umkc.edu",
        full_name="Dr. Nguyen",
        role="instructor",
        department="CS",
    )
    inst2 = User(
        username="other_inst",
        email="inst2@umkc.edu",
        full_name="Dr. Patel",
        role="instructor",
        department="CS",
    )
    session.add_all([inst1, inst2])

    c1 = Course(
        course_code="CS 5551",
        course_name="Advanced Software Engineering",
        department="CS",
        expected_enrollment=35,
    )
    c2 = Course(
        course_code="CS 5525",
        course_name="Cloud Computing",
        department="CS",
        expected_enrollment=35,
    )
    session.add_all([c1, c2])

    sem = Semester(
        semester_id=1,
        name="Fall 2024",
        start_date="2024-08-20",
        end_date="2024-12-15",
    )
    session.add(sem)

    slot1 = TimeSlot(day_pattern="TR", start_time="09:00", end_time="10:15")
    slot2 = TimeSlot(day_pattern="TR", start_time="13:00", end_time="14:15")
    session.add_all([slot1, slot2])
    session.commit()

    s1 = Schedule(
        semester_id=sem.id,
        course_id=c1.id,
        user_id=inst1.id,
        room_id=room1.id,
        time_slot_id=slot1.id,
        status="confirmed",
    )
    s2 = Schedule(
        semester_id=sem.id,
        course_id=c2.id,
        user_id=inst2.id,
        room_id=room2.id,
        time_slot_id=slot2.id,
        status="confirmed",
    )
    session.add_all([s1, s2])
    session.commit()

    return {
        "s1": s1,
        "s2": s2,
        "room1": room1,
        "room2": room2,
        "inst1": inst1,
        "inst2": inst2,
        "slot1": slot1,
        "slot2": slot2,
    }


def test_create_and_filter_edit_requests(client, session):
    fx = _seed_edit_request_fixture(session)

    r1 = client.post(
        "/api/v1/edit-requests",
        json={
            "schedule_id": fx["s1"].id,
            "requester_id": fx["inst1"].id,
            "requested_changes": "Move to afternoon slot in HH-202",
            "proposed_room_id": fx["room2"].id,
        },
    )
    assert r1.status_code == 201
    body = r1.json()
    assert body["status"] == "pending"
    assert body["requested_changes"] == "Move to afternoon slot in HH-202"
    assert body["proposed_room_id"] == fx["room2"].id
    assert body["created_at"] is not None

    r2 = client.post(
        "/api/v1/edit-requests",
        json={
            "schedule_id": fx["s2"].id,
            "requester_id": fx["inst2"].id,
            "requested_changes": "Swap to morning slot",
        },
    )
    assert r2.status_code == 201

    by_requester = client.get(
        f"/api/v1/edit-requests?requester_id={fx['inst1'].id}"
    ).json()
    assert len(by_requester) == 1
    assert by_requester[0]["id"] == body["id"]

    by_sched = client.get(
        f"/api/v1/edit-requests?schedule_id={fx['s2'].id}"
    ).json()
    assert len(by_sched) == 1
    assert by_sched[0]["requester_id"] == fx["inst2"].id


def test_approve_edit_request_updates_schedule_row(client, session):
    fx = _seed_edit_request_fixture(session)

    created = client.post(
        "/api/v1/edit-requests",
        json={
            "schedule_id": fx["s1"].id,
            "requester_id": fx["inst1"].id,
            "requested_changes": "Switch room to HH-202 in morning slot",
            "proposed_room_id": fx["room2"].id,
            "proposed_time_slot_id": fx["slot1"].id,
        },
    ).json()

    reviewed = client.patch(
        f"/api/v1/edit-requests/{created['id']}/review",
        json={
            "status": "approved",
            "reviewer_notes": "Room HH-202 is free at 09:00",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"
    assert reviewed.json()["reviewer_notes"] == "Room HH-202 is free at 09:00"

    schedules = client.get(
        f"/api/v1/schedules?semester_id={fx['s1'].semester_id}"
    ).json()
    sched = next(s for s in schedules if s["id"] == fx["s1"].id)
    assert sched["room_number"] == "HH-202"
    assert sched["status"] == "revised"

    again = client.patch(
        f"/api/v1/edit-requests/{created['id']}/review",
        json={"status": "rejected"},
    )
    assert again.status_code == 409


def test_approve_edit_request_conflict_returns_409(client, session):
    fx = _seed_edit_request_fixture(session)

    created = client.post(
        "/api/v1/edit-requests",
        json={
            "schedule_id": fx["s1"].id,
            "requester_id": fx["inst1"].id,
            "requested_changes": "Move to HH-202 at 13:00",
            "proposed_room_id": fx["room2"].id,
            "proposed_time_slot_id": fx["slot2"].id,
        },
    ).json()

    conflict = client.patch(
        f"/api/v1/edit-requests/{created['id']}/review",
        json={"status": "approved"},
    )
    assert conflict.status_code == 409
    assert "already booked" in conflict.json()["detail"]


def test_reject_and_delete_edit_request(client, session):
    fx = _seed_edit_request_fixture(session)

    created = client.post(
        "/api/v1/edit-requests",
        json={
            "schedule_id": fx["s1"].id,
            "requester_id": fx["inst1"].id,
            "requested_changes": "Requesting evening slot",
        },
    ).json()

    rejected = client.patch(
        f"/api/v1/edit-requests/{created['id']}/review",
        json={"status": "rejected", "reviewer_notes": "Keep morning section"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    del_resp = client.delete(f"/api/v1/edit-requests/{created['id']}")
    assert del_resp.status_code == 204
    assert client.get(f"/api/v1/edit-requests/{created['id']}").status_code == 404
