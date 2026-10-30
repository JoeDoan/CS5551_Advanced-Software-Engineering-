import csv
import io

from app.models.entities import Semester


def test_export_summary_and_department_breakdown(client):
    """GET /export/summary returns structured department, day, and status counts."""
    client.post("/api/v1/admin/seed")

    resp = client.get("/api/v1/export/summary?semester_id=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["semester_id"] == 1
    assert body["total_events"] == 40
    assert body["unique_instructors"] == 20
    assert sum(body["courses_by_department"].values()) == 40
    assert body["events_by_status"].get("confirmed") == 40

    cs_only = client.get("/api/v1/export/summary?semester_id=1&department=CS")
    assert cs_only.status_code == 200
    assert list(cs_only.json()["courses_by_department"].keys()) == ["CS"]


def test_export_schedules_csv_full_and_filtered(client):
    """GET /export/schedules.csv returns RFC 4180 CSV for full or filtered courses."""
    client.post("/api/v1/admin/seed")

    resp = client.get("/api/v1/export/schedules.csv?semester_id=1")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "schedule_semester_1.csv" in resp.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == [
        "Schedule ID",
        "Semester ID",
        "Course Code",
        "Course Name",
        "Department",
        "Instructor",
        "Room",
        "Day Pattern",
        "Start Time",
        "End Time",
        "Status",
    ]
    assert len(rows) == 41

    cs_resp = client.get(
        "/api/v1/export/schedules.csv?semester_id=1&department=CS"
    )
    assert cs_resp.status_code == 200
    cs_rows = list(csv.reader(io.StringIO(cs_resp.text)))
    assert 1 < len(cs_rows) < 41
    for data_row in cs_rows[1:]:
        assert data_row[4] == "CS"


def test_export_schedules_ics_calendar_stream(client):
    """GET /export/schedules.ics returns RFC 5545 VCALENDAR with 40 VEVENT blocks."""
    client.post("/api/v1/admin/seed")

    resp = client.get("/api/v1/export/schedules.ics?semester_id=1")
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["content-type"]
    assert "schedule_semester_1.ics" in resp.headers["content-disposition"]

    text = resp.text
    assert text.startswith("BEGIN:VCALENDAR")
    assert "PRODID:-//UMKC OptiSched//Course Timetable Scheduler//EN" in text
    assert text.count("BEGIN:VEVENT") == 40
    assert "RRULE:FREQ=WEEKLY;BYDAY=" in text
    assert text.strip().endswith("END:VCALENDAR")


def test_export_endpoints_unknown_semester_404(client):
    """Export endpoints return 404 when semester_id does not exist."""
    client.post("/api/v1/admin/seed")
    assert client.get("/api/v1/export/summary?semester_id=99").status_code == 404
    assert (
        client.get("/api/v1/export/schedules.csv?semester_id=99").status_code == 404
    )
    assert (
        client.get("/api/v1/export/schedules.ics?semester_id=99").status_code == 404
    )


def test_clone_semester_schedules_and_conflict_guard(client, session):
    """POST /schedules/clone-semester copies schedules and enforces overwrite guard."""
    client.post("/api/v1/admin/seed")

    sem7 = Semester(
        id=7,
        semester_id=7,
        name="Fall 2027",
        start_date="2027-08-20",
        end_date="2027-12-15",
        is_active=False,
    )
    session.add(sem7)
    session.commit()

    clone_resp = client.post(
        "/api/v1/schedules/clone-semester",
        json={
            "source_semester_id": 1,
            "target_semester_id": 7,
            "overwrite": False,
        },
    )
    assert clone_resp.status_code == 201
    body = clone_resp.json()
    assert body["cloned_count"] == 40
    assert body["target_semester_id"] == 7

    sem7_schedules = client.get("/api/v1/schedules?semester_id=7").json()
    assert len(sem7_schedules) == 40

    conflict_resp = client.post(
        "/api/v1/schedules/clone-semester",
        json={
            "source_semester_id": 1,
            "target_semester_id": 7,
            "overwrite": False,
        },
    )
    assert conflict_resp.status_code == 409

    overwrite_resp = client.post(
        "/api/v1/schedules/clone-semester",
        json={
            "source_semester_id": 1,
            "target_semester_id": 7,
            "overwrite": True,
        },
    )
    assert overwrite_resp.status_code == 201
    assert len(client.get("/api/v1/schedules?semester_id=7").json()) == 40


def test_clone_semester_validation_errors(client):
    """Cloning identical semesters returns 422 and unknown semesters return 404."""
    client.post("/api/v1/admin/seed")

    same_resp = client.post(
        "/api/v1/schedules/clone-semester",
        json={"source_semester_id": 1, "target_semester_id": 1},
    )
    assert same_resp.status_code == 422

    missing_resp = client.post(
        "/api/v1/schedules/clone-semester",
        json={"source_semester_id": 1, "target_semester_id": 99},
    )
    assert missing_resp.status_code == 404
    missing_src = client.post(
        "/api/v1/schedules/clone-semester",
        json={"source_semester_id": 99, "target_semester_id": 1},
    )
    assert missing_src.status_code == 404
