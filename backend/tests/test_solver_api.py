from fastapi.testclient import TestClient


def test_solver_run_success_and_persists_schedules(client: TestClient):
    """AC 2.1: POST /solver/run solves a semester and persists 40 course events."""
    client.post("/api/v1/admin/seed")

    response = client.post("/api/v1/solver/run", json={"semester_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("OPTIMAL", "FEASIBLE")
    assert data["semester_id"] == 1
    assert data["scheduled_count"] == 40
    assert data["wall_time_seconds"] >= 0
    assert 0 <= data["satisfaction_rate"] <= 100

    events = client.get("/api/v1/schedules?semester_id=1").json()
    assert len(events) == 40
    assert events[0]["status"] == "confirmed"


def test_solver_rerun_replaces_instead_of_duplicating(client: TestClient):
    """Re-running a semester replaces its rows and leaves other semesters alone."""
    client.post("/api/v1/admin/seed")
    client.post("/api/v1/solver/run", json={"semester_id": 1})
    client.post("/api/v1/solver/run", json={"semester_id": 1})

    assert len(client.get("/api/v1/schedules?semester_id=1").json()) == 40
    assert len(client.get("/api/v1/schedules?semester_id=2").json()) == 40


def test_solver_run_invalid_semester_returns_404(client: TestClient):
    """AC 2.2: A non-existent semester returns 404."""
    client.post("/api/v1/admin/seed")

    response = client.post("/api/v1/solver/run", json={"semester_id": 999})
    assert response.status_code == 404
    assert "Semester 999 does not exist" in response.json()["detail"]


def test_solver_run_infeasible_returns_422(client: TestClient):
    """AC 2.3: Over-constrained teaching-load bounds return 422."""
    client.post("/api/v1/admin/seed")

    response = client.post(
        "/api/v1/solver/run",
        json={
            "semester_id": 1,
            "min_courses_per_instructor": 3,
            "max_courses_per_instructor": 1,
        },
    )
    assert response.status_code == 422
    assert "feasible" in response.json()["detail"].lower()


def test_solver_enforce_zero_violations_flag_returns_422(client: TestClient):
    client.post("/api/v1/admin/seed")
    response = client.post(
        "/api/v1/solver/run", json={"semester_id": 1, "enforce_zero_violations": True}
    )
    assert response.status_code == 422


def test_users_and_semesters_directory_endpoints(client: TestClient):
    """GET /users and GET /semesters return the seeded records."""
    client.post("/api/v1/admin/seed")

    users = client.get("/api/v1/users?role=instructor")
    assert users.status_code == 200
    assert len(users.json()) == 20
    assert client.get("/api/v1/users?role=admin").json() == []

    semesters = client.get("/api/v1/semesters")
    assert semesters.status_code == 200
    assert [s["semester_id"] for s in semesters.json()] == [1, 2, 3, 4, 5, 6]


def test_seeded_and_solved_schedules_preserve_mw_and_tr_day_patterns(
    client: TestClient,
):
    """Seeded and CP-SAT solved schedules include both MW and TR meeting patterns."""
    client.post("/api/v1/admin/seed")

    seeded_events = client.get("/api/v1/schedules?semester_id=1").json()
    seeded_patterns = {e["day_pattern"] for e in seeded_events}
    assert "MW" in seeded_patterns
    assert "TR" in seeded_patterns

    solve_resp = client.post("/api/v1/solver/run", json={"semester_id": 1})
    assert solve_resp.status_code == 200

    solved_events = client.get("/api/v1/schedules?semester_id=1").json()
    solved_patterns = {e["day_pattern"] for e in solved_events}
    assert "MW" in solved_patterns
    assert "TR" in solved_patterns


def test_general_semester_preference_overrides_legacy_seeded_course_preferences(
    client: TestClient,
):
    """General preference (course_id=None) overrides legacy per-course preferences."""
    client.post("/api/v1/admin/seed")

    pref_resp = client.post(
        "/api/v1/preferences",
        json={
            "user_id": 1,
            "semester_id": 5,
            "course_id": None,
            "preferred_days": ["M", "F"],
            "preferred_slots": ["09:30-10:45", "14:00-15:15"],
        },
    )
    assert pref_resp.status_code in (200, 201)

    solve_resp = client.post("/api/v1/solver/run", json={"semester_id": 5})
    assert solve_resp.status_code == 200

    events = client.get("/api/v1/schedules?semester_id=5").json()
    lee_events = [e for e in events if e["user_id"] == 1]
    assert len(lee_events) >= 1
    assert all(e["day_pattern"] == "MF" for e in lee_events)
    assert {
        f"{e['start_time']}-{e['end_time']}" for e in lee_events
    } <= {"09:30-10:45", "14:00-15:15"}

    fairness = client.get("/api/v1/analytics/fairness?semester_id=5").json()
    lee_fairness = next(
        item for item in fairness["instructors"] if item["user_id"] == 1
    )
    assert lee_fairness["preferred_day_matches"] == len(lee_events)


def test_three_tier_preference_precedence_and_deletion(client: TestClient):
    """Tier 1 course override beats Tier 2 general; deletion restores Tier 2."""
    client.post("/api/v1/admin/seed")
    client.put(
        "/api/v1/course-assignments",
        json={"semester_id": 5, "user_id": 1, "course_ids": [1, 16]},
    )

    gen_resp = client.post(
        "/api/v1/preferences",
        json={
            "user_id": 1,
            "semester_id": 5,
            "course_id": None,
            "preferred_days": ["M", "W"],
            "preferred_slots": ["11:00-12:15"],
        },
    )
    assert gen_resp.status_code in (200, 201)

    c16_resp = client.post(
        "/api/v1/preferences",
        json={
            "user_id": 1,
            "semester_id": 5,
            "course_id": 16,
            "preferred_days": ["T", "R"],
            "preferred_slots": ["19:00-20:15"],
        },
    )
    assert c16_resp.status_code in (200, 201)
    c16_pref_id = c16_resp.json()["id"]
    assert c16_resp.json()["preference_rank"] == 1

    assert client.post("/api/v1/solver/run", json={"semester_id": 5}).status_code == 200
    events = client.get("/api/v1/schedules?semester_id=5").json()
    lee_by_cid = {e["course_id"]: e for e in events if e["user_id"] == 1}
    assert lee_by_cid[1]["day_pattern"] == "MW"
    assert (
        f"{lee_by_cid[1]['start_time']}-{lee_by_cid[1]['end_time']}" == "11:00-12:15"
    )
    assert lee_by_cid[16]["day_pattern"] == "TR"
    assert (
        f"{lee_by_cid[16]['start_time']}-{lee_by_cid[16]['end_time']}" == "19:00-20:15"
    )

    assert client.delete(f"/api/v1/preferences/{c16_pref_id}").status_code == 204
    assert client.post("/api/v1/solver/run", json={"semester_id": 5}).status_code == 200
    after_del = {
        e["course_id"]: e
        for e in client.get("/api/v1/schedules?semester_id=5").json()
        if e["user_id"] == 1
    }
    assert after_del[16]["day_pattern"] == "MW"
