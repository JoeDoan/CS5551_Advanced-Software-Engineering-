from fastapi.testclient import TestClient


def test_simulate_multi_semester_sequential_run(client: TestClient):
    """POST /solver/simulate runs across multiple semesters and persists schedules."""
    client.post("/api/v1/admin/seed")

    resp = client.post("/api/v1/solver/simulate", json={"semester_ids": [1, 2]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["semesters_simulated"] == 2
    assert data["total_scheduled_events"] == 80
    assert len(data["results"]) == 2
    assert 0 <= data["average_satisfaction_rate"] <= 100
    assert len(data["final_priorities"]) == 20


def test_simulate_priority_carryover_updates_user_priority_scores(client: TestClient):
    """Priority deltas from Semester 1 carry into Semester 2 and update User rows."""
    client.post("/api/v1/admin/seed")

    resp = client.post(
        "/api/v1/solver/simulate",
        json={"semester_ids": [1, 2], "reset_priorities_before_run": True},
    )
    assert resp.status_code == 200
    data = resp.json()

    sem1_updates = {
        u["user_id"]: u for u in data["results"][0]["priority_updates"]
    }
    sem2_updates = {
        u["user_id"]: u for u in data["results"][1]["priority_updates"]
    }

    for uid, u1 in sem1_updates.items():
        u2 = sem2_updates[uid]
        assert u2["old_priority"] == u1["new_priority"]
        if u1["satisfaction_rate"] is not None and u1["satisfaction_rate"] < 100.0:
            assert u1["delta"] > 0
            assert u1["new_priority"] > u1["old_priority"]
        elif u1["satisfaction_rate"] == 100.0:
            assert u1["new_priority"] <= u1["old_priority"]
            assert u1["delta"] <= 0

    users = client.get("/api/v1/users?role=instructor").json()
    for user in users:
        uid = user["id"]
        assert user["priority_score"] == sem2_updates[uid]["new_priority"]


def test_simulate_preserves_existing_db_priorities_when_reset_false(
    client: TestClient,
):
    """When reset_priorities_before_run is False, start from SQLite priority_score."""
    client.post("/api/v1/admin/seed")

    first = client.post(
        "/api/v1/solver/simulate",
        json={"semester_ids": [1], "reset_priorities_before_run": True},
    ).json()
    sem1_map = {
        u["user_id"]: u["new_priority"]
        for u in first["results"][0]["priority_updates"]
    }

    second = client.post(
        "/api/v1/solver/simulate",
        json={"semester_ids": [2], "reset_priorities_before_run": False},
    )
    assert second.status_code == 200
    for u in second.json()["results"][0]["priority_updates"]:
        assert u["old_priority"] == sem1_map[u["user_id"]]


def test_simulate_invalid_semester_returns_404(client: TestClient):
    """Unknown semester ID in simulation list returns 404."""
    client.post("/api/v1/admin/seed")
    resp = client.post("/api/v1/solver/simulate", json={"semester_ids": [1, 99]})
    assert resp.status_code == 404
    assert "Semester 99 does not exist" in resp.json()["detail"]


def test_simulate_infeasible_bounds_returns_422(client: TestClient):
    """Invalid teaching load bounds (max < min) return 422."""
    client.post("/api/v1/admin/seed")
    resp = client.post(
        "/api/v1/solver/simulate",
        json={
            "semester_ids": [1],
            "min_courses_per_instructor": 3,
            "max_courses_per_instructor": 1,
        },
    )
    assert resp.status_code == 422
