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
        json={"semester_id": 1, "min_courses_per_instructor": 3, "max_courses_per_instructor": 1},
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
