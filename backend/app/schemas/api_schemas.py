from enum import Enum
import re
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator


class RoomType(str, Enum):
    lecture = "lecture"
    lab = "lab"
    seminar = "seminar"
    auditorium = "auditorium"


DAY_ALIASES = {
    "MONDAY": "M",
    "TUESDAY": "T",
    "WEDNESDAY": "W",
    "THURSDAY": "R",
    "FRIDAY": "F",
    "MON": "M",
    "TUE": "T",
    "WED": "W",
    "THU": "R",
    "FRI": "F",
    "M": "M",
    "T": "T",
    "W": "W",
    "R": "R",
    "F": "F",
}


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str


class CourseBase(BaseModel):
    course_code: str = Field(..., min_length=2, max_length=20)
    course_name: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=20)
    credits: int = Field(default=3, ge=1, le=6)
    expected_enrollment: int = Field(default=30, ge=1, le=500)
    requires_lab: bool = False


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    course_code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    course_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    department: Optional[str] = Field(default=None, min_length=2, max_length=20)
    credits: Optional[int] = Field(default=None, ge=1, le=6)
    expected_enrollment: Optional[int] = Field(default=None, ge=1, le=500)
    requires_lab: Optional[bool] = None


class CourseResponse(CourseBase):
    id: int


class RoomBase(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    capacity: int = Field(..., ge=1, le=1000)
    room_type: RoomType = Field(default=RoomType.lecture)
    building_id: int = Field(..., gt=0)


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    room_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    capacity: Optional[int] = Field(default=None, ge=1, le=1000)
    room_type: Optional[RoomType] = None
    building_id: Optional[int] = Field(default=None, gt=0)


class RoomResponse(RoomBase):
    id: int
    building_name: Optional[str] = None


class TimeSlotResponse(BaseModel):
    id: int
    day_pattern: str
    start_time: str
    end_time: str
    slot_label: Optional[str] = None
    pattern_type: str = "TR_75"
    level: Optional[str] = None


class PreferenceCreate(BaseModel):
    user_id: int
    semester_id: int
    course_id: Optional[int] = None
    preferred_days: List[str] = Field(default_factory=list)
    preferred_slot_ids: List[int] = Field(default_factory=list)
    preferred_slots: List[str] = Field(default_factory=list)
    preferred_rooms: List[str] = Field(default_factory=list)

    @field_validator("preferred_days")
    @classmethod
    def validate_days(cls, v: List[str]) -> List[str]:
        out = []
        for d in v:
            key = DAY_ALIASES.get(d.strip().upper(), d.strip().upper())
            if not re.fullmatch(r"[MTWRF]{1,5}", key) or len(set(key)) != len(key):
                raise ValueError(f"Invalid day: {d}")
            out.append(key)
        return out


class PreferenceResponse(BaseModel):
    id: int
    user_id: int
    semester_id: int
    course_id: Optional[int] = None
    preferred_days: Union[List[str], str, None] = None
    preferred_slots: Union[List[str], str, None] = None
    preferred_rooms: Union[List[str], str, None] = None
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
