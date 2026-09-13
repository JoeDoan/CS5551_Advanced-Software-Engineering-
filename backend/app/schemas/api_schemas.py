from typing import Optional, List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str


class CourseBase(BaseModel):
    course_code: str
    course_name: str
    department: str
    credits: int = 3
    expected_enrollment: int = 30
    requires_lab: bool = False


class CourseResponse(CourseBase):
    id: int


class RoomBase(BaseModel):
    room_number: str
    capacity: int
    room_type: str = "lecture"
    building_id: int


class RoomResponse(RoomBase):
    id: int


class PreferenceCreate(BaseModel):
    user_id: int
    semester_id: int
    course_id: Optional[int] = None
    preferred_days: List[str] = Field(default_factory=list)
    preferred_slots: List[str] = Field(default_factory=list)
    preferred_rooms: List[str] = Field(default_factory=list)


class PreferenceResponse(BaseModel):
    id: int
    user_id: int
    semester_id: int
    course_id: Optional[int] = None
    preferred_days: Optional[str] = None
    preferred_slots: Optional[str] = None
    preferred_rooms: Optional[str] = None
    preference_rank: int = 1


class ScheduleEventResponse(BaseModel):
    id: int
    semester_id: int
    course_id: int
    course_code: str
    course_name: str
    instructor_name: str
    room_number: str
    day_pattern: str
    start_time: str
    end_time: str
    status: str = "confirmed"
