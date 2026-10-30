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


def test_fairness_and_utilization_analytics_on_seeded_data(client):
    """Fairness and utilization endpoints return valid Gini and room metrics."""
    client.post("/api/v1/admin/seed")

    fair_resp = client.get("/api/v1/analytics/fairness?semester_id=1")
    assert fair_resp.status_code == 200
    fair_data = fair_resp.json()
    assert fair_data["semester_id"] == 1
    assert fair_data["total_instructors"] == 20
    assert fair_data["total_scheduled_courses"] == 40
    assert 0.0 <= fair_data["priority_gini_index"] <= 1.0
    assert 0.0 <= fair_data["workload_gini_index"] <= 1.0
    assert len(fair_data["instructors"]) == 20
    assert len(fair_data["departments"]) >= 3

    util_resp = client.get("/api/v1/analytics/utilization?semester_id=1")
    assert util_resp.status_code == 200
    util_data = util_resp.json()
    assert util_data["semester_id"] == 1
    assert util_data["total_rooms"] == 12
    assert util_data["overall_slot_utilization_pct"] > 0.0
    assert util_data["overall_seat_occupancy_pct"] > 0.0
    assert len(util_data["rooms"]) == 12


def test_conflict_audit_clean_schedule_has_zero_hard_violations(client, session):
    """A valid schedule with distinct room/slot assignments is conflict-free."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()

    bldg = Building(campus_id=campus.id, name="Flarsheim Hall", code="FH")
    session.add(bldg)
    session.commit()

    r1 = Room(
        building_id=bldg.id, room_number="FH-101", capacity=50, room_type="lecture"
    )
    r2 = Room(
        building_id=bldg.id, room_number="FH-202L", capacity=40, room_type="lab"
    )
    session.add_all([r1, r2])

    inst1 = User(
        username="inst_clean1",
        email="c1@umkc.edu",
        full_name="Dr. Clean One",
        role="instructor",
        department="CS",
    )
    inst2 = User(
        username="inst_clean2",
        email="c2@umkc.edu",
        full_name="Dr. Clean Two",
        role="instructor",
        department="ECE",
    )
    session.add_all([inst1, inst2])

    c1 = Course(
        course_code="CS 101",
        course_name="Intro to CS",
        department="CS",
        expected_enrollment=35,
        requires_lab=False,
    )
    c2 = Course(
        course_code="ECE 201L",
        course_name="Circuits Lab",
        department="ECE",
        expected_enrollment=25,
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

    slot1 = TimeSlot(day_pattern="MWF", start_time="09:00", end_time="09:50")
    slot2 = TimeSlot(day_pattern="TR", start_time="11:00", end_time="12:15")
    session.add_all([slot1, slot2])
    session.commit()

    session.add_all(
        [
            Schedule(
                semester_id=sem.id,
                course_id=c1.id,
                user_id=inst1.id,
                room_id=r1.id,
                time_slot_id=slot1.id,
                status="confirmed",
            ),
            Schedule(
                semester_id=sem.id,
                course_id=c2.id,
                user_id=inst2.id,
                room_id=r2.id,
                time_slot_id=slot2.id,
                status="confirmed",
            ),
        ]
    )
    session.commit()

    resp = client.get(f"/api/v1/analytics/conflicts?semester_id={sem.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_conflict_free"] is True
    assert body["hard_violation_count"] == 0
    assert body["total_schedules_audited"] == 2


def test_conflict_audit_detects_double_booking_capacity_and_lab_mismatch(
    client, session
):
    """Corrupted schedule rows trigger double-booking, capacity, and lab violations."""
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()

    bldg = Building(campus_id=campus.id, name="Flarsheim Hall", code="FH")
    session.add(bldg)
    session.commit()

    tiny_lecture_room = Room(
        building_id=bldg.id, room_number="FH-105", capacity=15, room_type="lecture"
    )
    session.add(tiny_lecture_room)

    inst1 = User(
        username="inst_a",
        email="a@umkc.edu",
        full_name="Dr. Alpha",
        role="instructor",
        department="CS",
    )
    session.add(inst1)

    c_large = Course(
        course_code="CS 303",
        course_name="Data Structures",
        department="CS",
        expected_enrollment=50,
        requires_lab=False,
    )
    c_lab = Course(
        course_code="ECE 448L",
        course_name="Embedded Systems Lab",
        department="ECE",
        expected_enrollment=10,
        requires_lab=True,
    )
    session.add_all([c_large, c_lab])

    sem = Semester(
        semester_id=1,
        name="Fall 2024",
        start_date="2024-08-20",
        end_date="2024-12-15",
    )
    session.add(sem)

    slot = TimeSlot(day_pattern="MWF", start_time="10:00", end_time="10:50")
    session.add(slot)
    session.commit()

    s1 = Schedule(
        semester_id=sem.id,
        course_id=c_large.id,
        user_id=inst1.id,
        room_id=tiny_lecture_room.id,
        time_slot_id=slot.id,
        status="confirmed",
    )
    s2 = Schedule(
        semester_id=sem.id,
        course_id=c_lab.id,
        user_id=inst1.id,
        room_id=tiny_lecture_room.id,
        time_slot_id=slot.id,
        status="confirmed",
    )
    session.add_all([s1, s2])
    session.commit()

    resp = client.get(f"/api/v1/analytics/conflicts?semester_id={sem.id}")
    assert resp.status_code == 200
    audit = resp.json()
    assert audit["is_conflict_free"] is False
    assert audit["hard_violation_count"] >= 4
    v_types = {v["violation_type"] for v in audit["violations"]}
    assert "ROOM_DOUBLE_BOOKING" in v_types
    assert "INSTRUCTOR_DOUBLE_BOOKING" in v_types
    assert "CAPACITY_OVERFLOW" in v_types
    assert "LAB_TYPE_MISMATCH" in v_types


def test_analytics_unknown_semester_returns_404(client):
    """Analytics endpoints return 404 for unknown semester ID."""
    client.post("/api/v1/admin/seed")
    assert client.get("/api/v1/analytics/fairness?semester_id=99").status_code == 404
    assert (
        client.get("/api/v1/analytics/utilization?semester_id=99").status_code == 404
    )
    assert client.get("/api/v1/analytics/conflicts?semester_id=99").status_code == 404
