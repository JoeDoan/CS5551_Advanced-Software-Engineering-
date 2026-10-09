from app.models.entities import Campus, Building, Room, Course, User, Semester, TimeSlot, Schedule


def test_create_room_success_with_building_name(client, session):
    """AC 4.1 & Fix 5: Create room returns 201 with populated building_name."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()

    bldg = Building(campus_id=campus.id, name="Flarsheim Hall", code="FH")
    session.add(bldg)
    session.commit()

    payload = {
        "building_id": bldg.id,
        "room_number": "FH 260",
        "capacity": 45,
        "room_type": "lecture",
    }
    resp = client.post("/api/v1/rooms", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["room_number"] == "FH 260"
    assert data["building_name"] == "Flarsheim Hall"


def test_create_room_capacity_boundary_validation(client, session):
    """AC 4.2: Capacity boundary checks (capacity >= 1)."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()
    bldg = Building(campus_id=campus.id, name="Haag Hall", code="HH")
    session.add(bldg)
    session.commit()

    # Capacity = 0 should fail with 422
    bad_payload = {
        "building_id": bldg.id,
        "room_number": "HH 100",
        "capacity": 0,
        "room_type": "lecture",
    }
    assert client.post("/api/v1/rooms", json=bad_payload).status_code == 422


def test_filter_rooms_by_capacity_and_type(client, session):
    """AC 4.3: Filter rooms by min_capacity and room_type."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()
    bldg = Building(campus_id=campus.id, name="Royall Hall", code="RH")
    session.add(bldg)
    session.commit()

    client.post("/api/v1/rooms", json={"building_id": bldg.id, "room_number": "RH 101", "capacity": 30, "room_type": "lecture"})
    client.post("/api/v1/rooms", json={"building_id": bldg.id, "room_number": "RH 202", "capacity": 65, "room_type": "lecture"})
    client.post("/api/v1/rooms", json={"building_id": bldg.id, "room_number": "RH 303", "capacity": 70, "room_type": "lab"})

    # Filter min_capacity=50
    resp_cap = client.get("/api/v1/rooms?min_capacity=50")
    assert resp_cap.status_code == 200
    assert len(resp_cap.json()) == 2

    # Filter room_type=lab
    resp_type = client.get("/api/v1/rooms?room_type=lab")
    assert resp_type.status_code == 200
    labs = resp_type.json()
    assert len(labs) == 1
    assert labs[0]["room_number"] == "RH 303"


def test_duplicate_room_in_same_building_conflict(client, session):
    """AC 4.4: Duplicate room number in same building returns 409 Conflict."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()
    bldg = Building(campus_id=campus.id, name="Haag Hall", code="HH")
    session.add(bldg)
    session.commit()

    payload = {"building_id": bldg.id, "room_number": "HH 201", "capacity": 40, "room_type": "lecture"}
    r1 = client.post("/api/v1/rooms", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/rooms", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


def test_create_room_unknown_building_not_found(client):
    """AC 4.5: Non-existent building ID returns 404 Not Found."""
    payload = {"building_id": 9999, "room_number": "NO 101", "capacity": 30, "room_type": "lecture"}
    resp = client.post("/api/v1/rooms", json=payload)
    assert resp.status_code == 404
    assert "Building ID 9999 not found" in resp.json()["detail"]


def test_update_and_delete_room(client, session):
    """AC 4.8 & AC 4.10: Update room attributes and delete room."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()
    bldg = Building(campus_id=campus.id, name="Flarsheim Hall", code="FH")
    session.add(bldg)
    session.commit()

    created = client.post(
        "/api/v1/rooms",
        json={"building_id": bldg.id, "room_number": "FH 100", "capacity": 30, "room_type": "lecture"},
    ).json()
    rid = created["id"]

    # Update capacity
    up_resp = client.put(f"/api/v1/rooms/{rid}", json={"capacity": 55})
    assert up_resp.status_code == 200
    assert up_resp.json()["capacity"] == 55

    # Delete
    del_resp = client.delete(f"/api/v1/rooms/{rid}")
    assert del_resp.status_code == 204

    # Subsequent GET returns 404
    assert client.get(f"/api/v1/rooms/{rid}").status_code == 404


def test_room_delete_guard_conflict(client, session):
    """AC 4.11: Deleting a room with active schedule references returns 409 Conflict."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()
    bldg = Building(campus_id=campus.id, name="Haag Hall", code="HH")
    session.add(bldg)
    session.commit()

    room = Room(building_id=bldg.id, room_number="HH 300", capacity=50)
    session.add(room)

    course = Course(course_code="CS 5599", course_name="Research", department="CS")
    session.add(course)

    user = User(username="prof2", email="prof2@umkc.edu", full_name="Dr. Taylor", department="CS")
    session.add(user)

    sem = Semester(semester_id=1, name="Fall 2024", start_date="2024-08-20", end_date="2024-12-15")
    session.add(sem)

    slot = TimeSlot(day_pattern="TR", start_time="10:00", end_time="11:15")
    session.add(slot)
    session.commit()

    sched = Schedule(
        semester_id=sem.id,
        course_id=course.id,
        user_id=user.id,
        room_id=room.id,
        time_slot_id=slot.id,
    )
    session.add(sched)
    session.commit()

    # Attempt delete -> 409
    del_resp = client.delete(f"/api/v1/rooms/{room.id}")
    assert del_resp.status_code == 409
    assert "used by a schedule" in del_resp.json()["detail"]
