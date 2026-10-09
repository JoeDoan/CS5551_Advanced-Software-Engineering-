from app.models.entities import Course, Schedule, User, Building, Campus, Room, TimeSlot, Semester


def test_create_course_success(client):
    """AC 3.1: Given valid payload, POST /api/v1/courses returns 201 with assigned ID."""
    payload = {
        "course_code": "CS 451",
        "course_name": "Software Engineering II",
        "department": "CS",
        "credits": 3,
        "expected_enrollment": 35,
        "requires_lab": False,
    }
    response = client.post("/api/v1/courses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["course_code"] == "CS 451"
    assert data["department"] == "CS"


def test_create_course_duplicate_conflict(client):
    """AC 3.2: Given existing course code, POST returns 409 Conflict."""
    payload = {
        "course_code": "CS 451",
        "course_name": "Software Engineering II",
        "department": "CS",
        "credits": 3,
        "expected_enrollment": 35,
        "requires_lab": False,
    }
    r1 = client.post("/api/v1/courses", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/courses", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


def test_filter_courses_by_department(client):
    """AC 3.3: Given multiple courses, GET /api/v1/courses?department=CS filters properly."""
    c1 = {"course_code": "CS 101", "course_name": "Intro to CS", "department": "CS", "credits": 3, "expected_enrollment": 50}
    c2 = {"course_code": "ECE 216", "course_name": "Circuits I", "department": "ECE", "credits": 4, "expected_enrollment": 30}
    c3 = {"course_code": "MATH 210", "course_name": "Calculus I", "department": "MATH", "credits": 4, "expected_enrollment": 45}

    client.post("/api/v1/courses", json=c1)
    client.post("/api/v1/courses", json=c2)
    client.post("/api/v1/courses", json=c3)

    resp = client.get("/api/v1/courses?department=CS")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["course_code"] == "CS 101"


def test_update_and_delete_course(client):
    """AC 3.4: PUT updates course attributes, DELETE removes it, subsequent GET returns 404."""
    payload = {
        "course_code": "CS 301",
        "course_name": "Data Structures",
        "department": "CS",
        "credits": 3,
        "expected_enrollment": 30,
        "requires_lab": False,
    }
    created = client.post("/api/v1/courses", json=payload).json()
    cid = created["id"]

    # Update enrollment to 40
    update_resp = client.put(f"/api/v1/courses/{cid}", json={"expected_enrollment": 40})
    assert update_resp.status_code == 200
    assert update_resp.json()["expected_enrollment"] == 40

    # Delete course
    del_resp = client.delete(f"/api/v1/courses/{cid}")
    assert del_resp.status_code == 204

    # Subsequent GET returns 404
    get_resp = client.get(f"/api/v1/courses/{cid}")
    assert get_resp.status_code == 404


def test_create_course_invalid_numbers_validation(client):
    """AC 3.5: Invalid credits (<1 or >6) or enrollment (<1 or >500) returns 422."""
    bad_credits = {
        "course_code": "CS 999",
        "course_name": "Invalid Credits",
        "department": "CS",
        "credits": 8,
        "expected_enrollment": 30,
    }
    assert client.post("/api/v1/courses", json=bad_credits).status_code == 422

    bad_enrollment = {
        "course_code": "CS 998",
        "course_name": "Invalid Enrollment",
        "department": "CS",
        "credits": 3,
        "expected_enrollment": 0,
    }
    assert client.post("/api/v1/courses", json=bad_enrollment).status_code == 422


def test_course_not_found(client):
    """AC 3.7: Querying non-existent course returns 404."""
    assert client.get("/api/v1/courses/9999").status_code == 404
    assert client.put("/api/v1/courses/9999", json={"course_name": "test"}).status_code == 404
    assert client.delete("/api/v1/courses/9999").status_code == 404


def test_course_delete_guard_conflict(client, session):
    """AC 3.8: Deleting a course with active schedule references returns 409 Conflict."""
    # Seed course, campus, building, room, user, semester, timeslot, schedule
    campus = Campus(name="Volker", code="VK")
    session.add(campus)
    session.commit()

    bldg = Building(campus_id=campus.id, name="Haag Hall", code="HH")
    session.add(bldg)
    session.commit()

    room = Room(building_id=bldg.id, room_number="101", capacity=40)
    session.add(room)

    course = Course(course_code="CS 5590", course_name="Special Topics", department="CS")
    session.add(course)

    user = User(username="prof1", email="prof1@umkc.edu", full_name="Dr. Smith", department="CS")
    session.add(user)

    sem = Semester(semester_id=1, name="Fall 2024", start_date="2024-08-20", end_date="2024-12-15")
    session.add(sem)

    slot = TimeSlot(day_pattern="MWF", start_time="09:00", end_time="09:50")
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
    del_resp = client.delete(f"/api/v1/courses/{course.id}")
    assert del_resp.status_code == 409
    assert "used by a schedule" in del_resp.json()["detail"]


def test_course_search_and_pagination(client):
    """AC 3.9 & AC 3.10: Search keyword and pagination."""
    client.post("/api/v1/courses", json={"course_code": "CS 201R", "course_name": "Discrete Structures", "department": "CS"})
    client.post("/api/v1/courses", json={"course_code": "CS 303", "course_name": "Data Structures Advanced", "department": "CS"})
    client.post("/api/v1/courses", json={"course_code": "MATH 300", "course_name": "Linear Algebra", "department": "MATH"})

    # Search by keyword "Structures"
    search_resp = client.get("/api/v1/courses?search=Structures")
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) == 2

    # Pagination: limit 1, offset 0
    p1 = client.get("/api/v1/courses?limit=1&offset=0").json()
    assert len(p1) == 1

    p2 = client.get("/api/v1/courses?limit=1&offset=1").json()
    assert len(p2) == 1
    assert p1[0]["id"] != p2[0]["id"]
