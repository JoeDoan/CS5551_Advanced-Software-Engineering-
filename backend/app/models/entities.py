from typing import Optional
from sqlmodel import SQLModel, Field


class Campus(SQLModel, table=True):
    __tablename__ = "campuses"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: str
    address: Optional[str] = None


class Building(SQLModel, table=True):
    __tablename__ = "buildings"
    id: Optional[int] = Field(default=None, primary_key=True)
    campus_id: int = Field(foreign_key="campuses.id")
    name: str
    code: str


class Room(SQLModel, table=True):
    __tablename__ = "rooms"
    id: Optional[int] = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="buildings.id")
    room_number: str
    capacity: int
    room_type: str = "lecture"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    full_name: str
    role: str = "instructor"  # admin, coordinator, instructor
    department: str
    priority_score: int = 100000


class Course(SQLModel, table=True):
    __tablename__ = "courses"
    id: Optional[int] = Field(default=None, primary_key=True)
    course_code: str
    course_name: str
    department: str
    credits: int = 3
    expected_enrollment: int = 30
    requires_lab: bool = False


class TimeSlot(SQLModel, table=True):
    __tablename__ = "time_slots"
    id: Optional[int] = Field(default=None, primary_key=True)
    day_pattern: str  # e.g., "MWF", "TR"
    start_time: str  # "09:00"
    end_time: str  # "09:50"
    slot_label: Optional[str] = None


class Semester(SQLModel, table=True):
    __tablename__ = "semesters"
    id: Optional[int] = Field(default=None, primary_key=True)
    semester_id: int
    name: str  # "Fall 2024"
    start_date: str
    end_date: str
    is_active: bool = False


class InstructorPreference(SQLModel, table=True):
    __tablename__ = "instructor_preferences"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    semester_id: int = Field(foreign_key="semesters.id")
    course_id: Optional[int] = Field(default=None, foreign_key="courses.id")
    preferred_days: Optional[str] = None
    preferred_slots: Optional[str] = None
    preferred_rooms: Optional[str] = None
    preference_rank: int = 1


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"
    id: Optional[int] = Field(default=None, primary_key=True)
    semester_id: int = Field(foreign_key="semesters.id")
    course_id: int = Field(foreign_key="courses.id")
    user_id: int = Field(foreign_key="users.id")
    room_id: int = Field(foreign_key="rooms.id")
    time_slot_id: int = Field(foreign_key="time_slots.id")
    status: str = "confirmed"  # tentative, confirmed, revised


class EditRequest(SQLModel, table=True):
    __tablename__ = "edit_requests"
    id: Optional[int] = Field(default=None, primary_key=True)
    schedule_id: int = Field(foreign_key="schedules.id")
    requester_id: int = Field(foreign_key="users.id")
    requested_changes: str
    status: str = "pending"  # pending, approved, rejected
    created_at: Optional[str] = None
