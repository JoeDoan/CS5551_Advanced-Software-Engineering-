import pytest
from app.models.entities import Course, Room, User, Semester, InstructorPreference


def test_course_model_instantiation():
    course = Course(
        course_code="CS 5551",
        course_name="Advanced Software Engineering",
        department="CS",
        credits=3,
        expected_enrollment=40,
        requires_lab=False,
    )
    assert course.course_code == "CS 5551"
    assert course.credits == 3
    assert not course.requires_lab


def test_room_model_instantiation():
    room = Room(
        building_id=1,
        room_number="FH 464",
        capacity=60,
        room_type="lab",
    )
    assert room.room_number == "FH 464"
    assert room.capacity == 60
    assert room.room_type == "lab"


def test_user_model_instantiation():
    user = User(
        username="ylee",
        email="lee@umkc.edu",
        full_name="Dr. Yugyung Lee",
        role="instructor",
        department="CS",
        priority_score=100000,
    )
    assert user.full_name == "Dr. Yugyung Lee"
    assert user.priority_score == 100000
