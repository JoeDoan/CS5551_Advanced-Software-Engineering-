from app.models.entities import User, Semester, Course, TimeSlot


def test_submit_preference_and_fetch_by_instructor(client, session):
    """AC 5.1 & AC 5.2: Submit valid preference returns 201; fetch by user_id returns preferences."""
    instructor = User(username="prof_lee", email="lee@umkc.edu", full_name="Dr. Lee", role="instructor", department="CS")
    session.add(instructor)
    semester = Semester(semester_id=1, name="Fall 2024", start_date="2024-08-20", end_date="2024-12-15")
    session.add(semester)
    course = Course(course_code="CS 5551", course_name="Advanced SE", department="CS")
    session.add(course)
    session.commit()

    payload = {
        "user_id": instructor.id,
        "semester_id": semester.id,
        "course_id": course.id,
        "preferred_days": ["MWF"],
        "preferred_slots": ["09:00-09:50"],
        "preferred_rooms": ["FH 260"],
    }
    resp = client.post("/api/v1/preferences", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["user_id"] == instructor.id
    assert data["preferred_days"] == ["MWF"]

    # Fetch by instructor
    fetch_resp = client.get(f"/api/v1/preferences?user_id={instructor.id}")
    assert fetch_resp.status_code == 200
    prefs = fetch_resp.json()
    assert len(prefs) == 1
    assert prefs[0]["course_id"] == course.id


def test_preference_resubmission_upsert_replaces(client, session):
    """AC 5.3 & Fix 6: Resubmitting preferences for the same user and course updates record and returns 200."""
    instructor = User(username="prof_derakh", email="derakh@umkc.edu", full_name="Dr. Derakhshani", role="instructor", department="CS")
    session.add(instructor)
    semester = Semester(semester_id=1, name="Fall 2024", start_date="2024-08-20", end_date="2024-12-15")
    session.add(semester)
    course = Course(course_code="CS 441", course_name="Programming Languages", department="CS")
    session.add(course)
    session.commit()

    payload1 = {
        "user_id": instructor.id,
        "semester_id": semester.id,
        "course_id": course.id,
        "preferred_days": ["TR"],
        "preferred_slots": ["10:00-11:15"],
    }
    r1 = client.post("/api/v1/preferences", json=payload1)
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    # Resubmit with new preferred days
    payload2 = {
        "user_id": instructor.id,
        "semester_id": semester.id,
        "course_id": course.id,
        "preferred_days": ["MWF"],
        "preferred_slots": ["13:00-13:50"],
    }
    r2 = client.post("/api/v1/preferences", json=payload2)
    assert r2.status_code == 200
    assert r2.json()["id"] == first_id
    assert r2.json()["preferred_days"] == ["MWF"]

    # Verify only 1 row exists
    all_prefs = client.get(f"/api/v1/preferences?user_id={instructor.id}").json()
    assert len(all_prefs) == 1


def test_preference_role_guard_forbidden(client, session):
    """AC 5.7: User with role != 'instructor' receives 403 Forbidden."""
    student = User(username="john_doe", email="john@umkc.edu", full_name="John Doe", role="coordinator", department="CS")
    session.add(student)
    semester = Semester(semester_id=1, name="Fall 2024", start_date="2024-08-20", end_date="2024-12-15")
    session.add(semester)
    session.commit()

    payload = {
        "user_id": student.id,
        "semester_id": semester.id,
        "preferred_days": ["MWF"],
    }
    resp = client.post("/api/v1/preferences", json=payload)
    assert resp.status_code == 403
    assert "Only instructors" in resp.json()["detail"]


def test_preference_user_and_semester_validation(client, session):
    """AC 5.6 & AC 5.8: Non-existent user or semester returns 404."""
    # Unknown user
    p1 = {"user_id": 9999, "semester_id": 1, "preferred_days": ["MWF"]}
    assert client.post("/api/v1/preferences", json=p1).status_code == 404

    # Unknown semester
    instructor = User(username="prof_x", email="x@umkc.edu", full_name="Dr. X", role="instructor", department="CS")
    session.add(instructor)
    session.commit()
    p2 = {"user_id": instructor.id, "semester_id": 9999, "preferred_days": ["MWF"]}
    assert client.post("/api/v1/preferences", json=p2).status_code == 404


def test_coordinator_overview_all_preferences(client, session):
    """AC 5.10: Coordinator can query GET /preferences without user_id to view all for semester."""
    u1 = User(username="inst1", email="i1@umkc.edu", full_name="Inst 1", role="instructor", department="CS")
    u2 = User(username="inst2", email="i2@umkc.edu", full_name="Inst 2", role="instructor", department="ECE")
    session.add(u1)
    session.add(u2)
    sem = Semester(semester_id=1, name="Fall 2024", start_date="2024-08-20", end_date="2024-12-15")
    session.add(sem)
    session.commit()

    client.post("/api/v1/preferences", json={"user_id": u1.id, "semester_id": sem.id, "preferred_days": ["MWF"]})
    client.post("/api/v1/preferences", json={"user_id": u2.id, "semester_id": sem.id, "preferred_days": ["TR"]})

    overview = client.get(f"/api/v1/preferences?semester_id={sem.id}").json()
    assert len(overview) == 2
