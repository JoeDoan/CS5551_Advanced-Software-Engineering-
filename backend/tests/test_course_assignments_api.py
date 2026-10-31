from app.api.v1.routes_preferences import course_level
from app.core.seeder import seed_database
from app.models.entities import User


def test_course_level_classifier_handles_3_and_4_digit_catalog_codes():
    for undergrad in ("CS 101", "CS 303", "CS 404", "CS 1010", "CS 4900"):
        assert course_level(undergrad) == "undergraduate"
    for grad in ("ECE 550", "CS 5551", "CS 5560"):
        assert course_level(grad) == "graduate"


def test_seeded_rooms_building_metadata_and_active_fall_2026_semester(client, session):
    seed_database(session=session)

    rooms = client.get("/api/v1/rooms").json()
    assert len(rooms) > 0
    assert all(r["building_name"] and r["building_code"] for r in rooms)
    fh_room = next(r for r in rooms if r["building_code"] == "FH")
    assert fh_room["building_name"] == "Flarsheim Hall"

    semesters = client.get("/api/v1/semesters").json()
    assert [s["semester_id"] for s in semesters] == [1, 2, 3, 4, 5, 6]
    fall_2026 = next(s for s in semesters if s["id"] == 5)
    assert fall_2026["name"] == "Fall 2026"
    assert fall_2026["is_active"] is True


def test_course_assignments_crud_validation_reset_and_extra_course_solver(
    client, session
):
    seed_database(session=session)

    coord_user = User(
        username="coord_only",
        email="coord_only@umkc.edu",
        full_name="Coord Only",
        role="coordinator",
        department="CS",
    )
    session.add(coord_user)
    session.commit()

    assert (
        client.put(
            "/api/v1/course-assignments",
            json={"semester_id": 999, "user_id": 1, "course_ids": [5]},
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/course-assignments",
            json={"semester_id": 5, "user_id": 9999, "course_ids": [5]},
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/course-assignments",
            json={"semester_id": 5, "user_id": coord_user.id, "course_ids": [5]},
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/v1/course-assignments",
            json={"semester_id": 5, "user_id": 1, "course_ids": [9999]},
        ).status_code
        == 404
    )

    created = client.post(
        "/api/v1/course-assignments",
        json={"semester_id": 5, "user_id": 1, "course_id": 14},
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["course_code"] == "CS 5551"
    assert created_body["course_level"] == "graduate"

    dup = client.post(
        "/api/v1/course-assignments",
        json={"semester_id": 5, "user_id": 1, "course_id": 14},
    )
    assert dup.status_code == 200
    assert dup.json()["id"] == created_body["id"]

    replaced = client.put(
        "/api/v1/course-assignments",
        json={"semester_id": 5, "user_id": 1, "course_ids": [5, 14, 16, 5]},
    )
    assert replaced.status_code == 200
    assert [r["course_id"] for r in replaced.json()] == [5, 14, 16]

    extra_course = client.post(
        "/api/v1/courses",
        json={
            "course_code": "ECE 550",
            "course_name": "Advanced Digital Systems",
            "department": "ECE",
            "credits": 3,
            "expected_enrollment": 25,
            "requires_lab": False,
        },
    ).json()
    extra_assign = client.post(
        "/api/v1/course-assignments",
        json={"semester_id": 5, "user_id": 7, "course_id": extra_course["id"]},
    )
    assert extra_assign.status_code == 201
    assert extra_assign.json()["course_level"] == "graduate"

    solved = client.post(
        "/api/v1/solver/run",
        json={"semester_id": 5, "max_courses_per_instructor": 2},
    )
    assert solved.status_code == 200, solved.text
    assert solved.json()["scheduled_count"] == 41

    sched_by_course = {
        row["course_id"]: row
        for row in client.get("/api/v1/schedules?semester_id=5").json()
    }
    assert sched_by_course[5]["user_id"] == 1
    assert sched_by_course[14]["user_id"] == 1
    assert sched_by_course[16]["user_id"] == 1
    assert sched_by_course[extra_course["id"]]["user_id"] == 7

    aid = extra_assign.json()["id"]
    assert client.delete(f"/api/v1/course-assignments/{aid}").status_code == 204
    assert client.delete(f"/api/v1/course-assignments/{aid}").status_code == 404

    seed_database(session=session, force_reset=True)
    assert client.get("/api/v1/course-assignments").json() == []
