from app.core.seeder import seed_database


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client, identifier: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_login_coordinator_and_faculty_and_invalid_credentials(client, session):
    """Coordinator and seeded faculty log in cleanly; invalid password returns 401."""
    counts = seed_database(session=session)
    assert counts["users"] == 20

    coord = _login(client, "coordinator@umkc.edu", "coordinator123")
    assert coord["token_type"] == "bearer"
    assert coord["user"]["role"] == "coordinator"
    assert coord["user"]["username"] == "coordinator"
    assert coord["user"]["linked_user_id"] is None

    coord_by_uname = client.post(
        "/api/v1/auth/login",
        json={"username": "COORDINATOR", "password": "coordinator123"},
    )
    assert coord_by_uname.status_code == 200

    faculty = _login(client, "leeyu@umkc.edu", "faculty123")
    assert faculty["user"]["role"] == "instructor"
    assert faculty["user"]["full_name"] == "Dr. Yugyung Lee"
    assert faculty["user"]["linked_user_id"] == 1

    bad_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "leeyu@umkc.edu", "password": "wrong-password"},
    )
    assert bad_pw.status_code == 401

    unknown = client.post(
        "/api/v1/auth/login",
        json={"identifier": "nobody@umkc.edu", "password": "faculty123"},
    )
    assert unknown.status_code == 401

    assert len(client.get("/api/v1/users").json()) == 20


def test_demo_accounts_and_session_lifecycle_revocation(client, session):
    """GET /auth/me validates live DB sessions and rejects revoked or missing tokens."""
    seed_database(session=session)

    demos = client.get("/api/v1/auth/demo-accounts")
    assert demos.status_code == 200
    demo_emails = {item["email"] for item in demos.json()}
    assert "coordinator@umkc.edu" in demo_emails
    assert "leeyu@umkc.edu" in demo_emails

    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get("/api/v1/auth/me", headers=_bearer("invalid.jwt.token")).status_code
        == 401
    )

    coord = _login(client, "coordinator@umkc.edu", "coordinator123")
    token = coord["access_token"]

    me_ok = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert me_ok.status_code == 200
    assert me_ok.json()["session_id"] == coord["session_id"]
    assert me_ok.json()["user"]["email"] == "coordinator@umkc.edu"

    logged_out = client.post("/api/v1/auth/logout", headers=_bearer(token))
    assert logged_out.status_code == 200
    assert logged_out.json()["status"] == "logged_out"
    assert logged_out.json()["revoked_session_id"] == coord["session_id"]

    me_after_logout = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert me_after_logout.status_code == 401


def test_strict_rbac_enforcement_for_unauthenticated_and_instructor_roles(
    client, session, monkeypatch
):
    """REQUIRE_AUTH=true enforces 401/403 RBAC and self-only preference mutations."""
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    seed_database(session=session)

    new_course_payload = {
        "course_code": "CS 5588",
        "course_name": "Distributed Systems Security",
        "department": "CS",
        "credits": 3,
        "expected_enrollment": 30,
        "requires_lab": False,
    }
    assert client.post("/api/v1/courses", json=new_course_payload).status_code == 401
    assert (
        client.post(
            "/api/v1/preferences",
            json={"user_id": 1, "semester_id": 1, "preferred_days": ["TR"]},
        ).status_code
        == 401
    )

    coord = _login(client, "coordinator@umkc.edu", "coordinator123")
    coord_headers = _bearer(coord["access_token"])

    faculty = _login(client, "leeyu@umkc.edu", "faculty123")
    faculty_headers = _bearer(faculty["access_token"])
    own_uid = faculty["user"]["linked_user_id"]
    assert own_uid == 1

    schedules = client.get("/api/v1/schedules?semester_id=1").json()
    er_resp = client.post(
        "/api/v1/edit-requests",
        headers=faculty_headers,
        json={
            "schedule_id": schedules[0]["id"],
            "requester_id": own_uid,
            "requested_changes": "Prefer afternoon lecture slot",
        },
    )
    assert er_resp.status_code == 201
    er_id = er_resp.json()["id"]

    assert (
        client.post(
            "/api/v1/courses", headers=faculty_headers, json=new_course_payload
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/schedules",
            headers=faculty_headers,
            json={
                "semester_id": 1,
                "course_id": 1,
                "user_id": 1,
                "room_id": 1,
                "time_slot_id": 7,
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/solver/run",
            headers=faculty_headers,
            json={"semester_id": 1},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/edit-requests/{er_id}/review",
            headers=faculty_headers,
            json={"status": "approved"},
        ).status_code
        == 403
    )

    own_pref = client.post(
        "/api/v1/preferences",
        headers=faculty_headers,
        json={"user_id": own_uid, "semester_id": 1, "preferred_days": ["MWF"]},
    )
    assert own_pref.status_code in (200, 201)

    other_pref = client.post(
        "/api/v1/preferences",
        headers=faculty_headers,
        json={"user_id": 2, "semester_id": 1, "preferred_days": ["TR"]},
    )
    assert other_pref.status_code == 403

    reviewed = client.patch(
        f"/api/v1/edit-requests/{er_id}/review",
        headers=coord_headers,
        json={"status": "rejected", "reviewer_notes": "Keep current slot"},
    )
    assert reviewed.status_code == 200


def test_coordinator_section_crud_cascade_delete_and_extra_course_solver(
    client, session, monkeypatch
):
    """Coordinator manages sections, cascade deletes, and extra-course solver runs."""
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    seed_database(session=session)

    coord = _login(client, "coordinator@umkc.edu", "coordinator123")
    headers = _bearer(coord["access_token"])

    created_course = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_code": "CS 5595",
            "course_name": "Agentic Software Systems",
            "department": "CS",
            "credits": 3,
            "expected_enrollment": 25,
            "requires_lab": False,
        },
    )
    assert created_course.status_code == 201
    new_cid = created_course.json()["id"]

    rooms = client.get("/api/v1/rooms?min_capacity=25").json()
    target_room_id = rooms[0]["id"]
    mwf_slot = next(
        s for s in client.get("/api/v1/time-slots").json() if s["day_pattern"] == "MWF"
    )

    created_sec = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "semester_id": 1,
            "course_id": new_cid,
            "user_id": 1,
            "room_id": target_room_id,
            "time_slot_id": mwf_slot["id"],
        },
    )
    assert created_sec.status_code == 201
    created_payload = created_sec.json()
    sec_id = created_payload["id"]
    assert created_payload["course_code"] == "CS 5595"
    assert created_payload["user_id"] == 1
    assert created_payload["room_id"] == target_room_id
    assert created_payload["time_slot_id"] == mwf_slot["id"]
    assert created_payload["department"] == "CS"

    conflict_sec = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "semester_id": 1,
            "course_id": new_cid,
            "user_id": 2,
            "room_id": target_room_id,
            "time_slot_id": mwf_slot["id"],
        },
    )
    assert conflict_sec.status_code == 409

    del_sec = client.delete(f"/api/v1/schedules/{sec_id}", headers=headers)
    assert del_sec.status_code == 204
    assert client.get(f"/api/v1/schedules/{sec_id}").status_code == 404

    solve_resp = client.post(
        "/api/v1/solver/run", headers=headers, json={"semester_id": 1}
    )
    assert solve_resp.status_code == 200
    assert solve_resp.json()["scheduled_count"] == 41

    sem1_events = client.get("/api/v1/schedules?semester_id=1").json()
    assert len(sem1_events) == 41
    extra_sched = next(e for e in sem1_events if e["course_id"] == new_cid)
    other_events = [e for e in sem1_events if e["id"] != extra_sched["id"]]
    assert all(
        not (
            e["room_number"] == extra_sched["room_number"]
            and e["day_pattern"] == extra_sched["day_pattern"]
            and e["start_time"] == extra_sched["start_time"]
        )
        for e in other_events
    )
    assert all(
        not (
            e["instructor_name"] == extra_sched["instructor_name"]
            and e["day_pattern"] == extra_sched["day_pattern"]
            and e["start_time"] == extra_sched["start_time"]
        )
        for e in other_events
    )
    client.post(
        "/api/v1/edit-requests",
        headers=headers,
        json={
            "schedule_id": extra_sched["id"],
            "requester_id": 1,
            "requested_changes": "Testing cascade cleanup",
        },
    )
    assert (
        client.delete(f"/api/v1/courses/{new_cid}", headers=headers).status_code == 409
    )

    cascade_del = client.delete(
        f"/api/v1/courses/{new_cid}?cascade=true", headers=headers
    )
    assert cascade_del.status_code == 204
    assert client.get(f"/api/v1/courses/{new_cid}").status_code == 404

    used_room_id = rooms[0]["id"]
    assert (
        client.delete(f"/api/v1/rooms/{used_room_id}", headers=headers).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/rooms/{used_room_id}?cascade=true", headers=headers
        ).status_code
        == 204
    )


def test_schedule_section_validation_404_422_and_expired_token_401(
    client, session, monkeypatch
):
    """POST /schedules enforces 404/422 constraints and expired JWT returns 401."""
    from datetime import timedelta
    from app.core.security import create_access_token

    monkeypatch.setenv("REQUIRE_AUTH", "true")
    seed_database(session=session)

    expired_jwt = create_access_token(
        {"sub": "1", "role": "coordinator", "jti": "expired-jti"},
        expires_delta=timedelta(seconds=-10),
    )
    assert (
        client.get("/api/v1/auth/me", headers=_bearer(expired_jwt)).status_code == 401
    )

    coord = _login(client, "coordinator@umkc.edu", "coordinator123")
    headers = _bearer(coord["access_token"])

    lab_course = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_code": "CS 5597L",
            "course_name": "Robotics Hardware Lab",
            "department": "CS",
            "credits": 4,
            "expected_enrollment": 400,
            "requires_lab": True,
        },
    ).json()

    lecture_room = next(
        r for r in client.get("/api/v1/rooms").json() if r["room_type"] == "lecture"
    )
    mwf_slot = next(
        s for s in client.get("/api/v1/time-slots").json() if s["day_pattern"] == "MWF"
    )

    assert (
        client.post(
            "/api/v1/schedules",
            headers=headers,
            json={
                "semester_id": 999,
                "course_id": lab_course["id"],
                "user_id": 1,
                "room_id": lecture_room["id"],
                "time_slot_id": mwf_slot["id"],
            },
        ).status_code
        == 404
    )

    cap_fail = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "semester_id": 1,
            "course_id": lab_course["id"],
            "user_id": 1,
            "room_id": lecture_room["id"],
            "time_slot_id": mwf_slot["id"],
        },
    )
    assert cap_fail.status_code == 422

    client.put(
        f"/api/v1/courses/{lab_course['id']}",
        headers=headers,
        json={"expected_enrollment": 10},
    )
    lab_fail = client.post(
        "/api/v1/schedules",
        headers=headers,
        json={
            "semester_id": 1,
            "course_id": lab_course["id"],
            "user_id": 1,
            "room_id": lecture_room["id"],
            "time_slot_id": mwf_slot["id"],
        },
    )
    assert lab_fail.status_code == 422

    assert client.delete("/api/v1/schedules/999999", headers=headers).status_code == 404
