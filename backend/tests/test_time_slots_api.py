from app.models.entities import TimeSlot


def test_time_slots_catalog_and_filtering(client, session):
    """AC 5.12 & Fix 4b: Time-slot catalog list and day pattern/level filtering."""
    s1 = TimeSlot(day_pattern="MWF", start_time="09:00", end_time="09:50", slot_label="Slot 1", pattern_type="MWF_50", level="undergraduate")
    s2 = TimeSlot(day_pattern="TR", start_time="10:00", end_time="11:15", slot_label="Slot 2", pattern_type="TR_75", level="graduate")
    s3 = TimeSlot(day_pattern="TR", start_time="13:00", end_time="14:15", slot_label="Slot 3", pattern_type="TR_75", level="undergraduate")
    session.add(s1)
    session.add(s2)
    session.add(s3)
    session.commit()

    # List all
    all_slots = client.get("/api/v1/time-slots").json()
    assert len(all_slots) == 3

    # Filter day_pattern=TR
    tr_slots = client.get("/api/v1/time-slots?day_pattern=TR").json()
    assert len(tr_slots) == 2
    for s in tr_slots:
        assert s["day_pattern"] == "TR"

    # Filter level=graduate
    grad_slots = client.get("/api/v1/time-slots?level=graduate").json()
    assert len(grad_slots) == 1
    assert grad_slots[0]["level"] == "graduate"
