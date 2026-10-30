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


def _seed_override_fixture(session):
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()

    bldg = Building(campus_id=campus.id, name="Flarsheim Hall", code="FH")
    session.add(bldg)
    session.commit()

    room_large = Room(
        building_id=bldg.id, room_number="FH-101", capacity=60, room_type="lecture"
    )
    room_free = Room(
        building_id=bldg.id, room_number="FH-102", capacity=60, room_type="lecture"
    )
    room_tiny = Room(
        building_id=bldg.id, room_number="FH-103", capacity=15, room_type="lecture"
    )
    room_lab = Room(
        building_id=bldg.id, room_number="FH-LAB1", capacity=40, room_type="lab"
    )
    session.add_all([room_large, room_free, room_tiny, room_lab])

    inst1 = User(
        username="inst1",
        email="inst1@umkc.edu",
        full_name="Dr. Alice",
        role="instructor",
        department="CS",
    )
    inst2 = User(
        username="inst2",
        email="inst2@umkc.edu",
        full_name="Dr. Bob",
        role="instructor",
        department="CS",
    )
    session.add_all([inst1, inst2])

    c1 = Course(
        course_code="CS 401",
        course_name="Algorithms",
        department="CS",
        expected_enrollment=40,
        requires_lab=False,
    )
    c2 = Course(
        course_code="CS 402L",
        course_name="Robotics Lab",
        department="CS",
        expected_enrollment=30,
        requires_lab=True,
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
    slot2 = TimeSlot(day_pattern="TR", start_time="10:30", end_time="11:45")
    session.add_all([slot1, slot2])
    session.commit()

    s1 = Schedule(
        semester_id=sem.id,
        course_id=c1.id,
        user_id=inst1.id,
        room_id=room_large.id,
        time_slot_id=slot1.id,
        status="confirmed",
    )
    s2 = Schedule(
        semester_id=sem.id,
        course_id=c2.id,
        user_id=inst2.id,
        room_id=room_lab.id,
        time_slot_id=slot2.id,
        status="confirmed",
    )
    session.add_all([s1, s2])
    session.commit()

    return {
        "s1": s1,
        "s2": s2,
        "room_large": room_large,
        "room_free": room_free,
        "room_tiny": room_tiny,
        "room_lab": room_lab,
        "inst1": inst1,
        "inst2": inst2,
        "slot1": slot1,
        "slot2": slot2,
    }


def test_get_single_schedule_by_id_and_404(client, session):
    fx = _seed_override_fixture(session)

    resp = client.get(f"/api/v1/schedules/{fx['s1'].id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["course_code"] == "CS 401"
    assert data["instructor_name"] == "Dr. Alice"
    assert data["room_number"] == "FH-101"

    assert client.get("/api/v1/schedules/9999").status_code == 404


def test_override_schedule_valid_room_and_slot(client, session):
    fx = _seed_override_fixture(session)

    resp = client.patch(
        f"/api/v1/schedules/{fx['s1'].id}",
        json={"room_id": fx["room_free"].id, "time_slot_id": fx["slot2"].id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["room_number"] == "FH-102"
    assert body["start_time"] == "10:30"
    assert body["status"] == "revised"


def test_override_schedule_room_and_instructor_conflict_409(client, session):
    fx = _seed_override_fixture(session)

    room_clash = client.patch(
        f"/api/v1/schedules/{fx['s1'].id}",
        json={"room_id": fx["room_lab"].id, "time_slot_id": fx["slot2"].id},
    )
    assert room_clash.status_code == 409
    assert "already booked" in room_clash.json()["detail"]

    inst_clash = client.patch(
        f"/api/v1/schedules/{fx['s1'].id}",
        json={
            "room_id": fx["room_free"].id,
            "time_slot_id": fx["slot2"].id,
            "user_id": fx["inst2"].id,
        },
    )
    assert inst_clash.status_code == 409
    assert "already assigned" in inst_clash.json()["detail"]


def test_override_schedule_capacity_and_lab_violations_422(client, session):
    fx = _seed_override_fixture(session)

    cap_resp = client.patch(
        f"/api/v1/schedules/{fx['s1'].id}",
        json={"room_id": fx["room_tiny"].id},
    )
    assert cap_resp.status_code == 422
    assert "capacity" in cap_resp.json()["detail"].lower()

    lab_resp = client.patch(
        f"/api/v1/schedules/{fx['s2'].id}",
        json={"room_id": fx["room_free"].id},
    )
    assert lab_resp.status_code == 422
    assert "lab" in lab_resp.json()["detail"].lower()
