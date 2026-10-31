from enum import Enum
import re
from typing import Dict, List, Optional, Union
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
    preferred_slot_ids: List[int] = Field(default_factory=list)
    preferred_rooms: Union[List[str], str, None] = None
    preference_rank: int = 1


class ScheduleEventResponse(BaseModel):
    id: int
    semester_id: int
    course_id: int
    user_id: Optional[int] = None
    room_id: Optional[int] = None
    time_slot_id: Optional[int] = None
    department: Optional[str] = None
    course_code: str
    course_name: str
    instructor_name: str
    room_number: str
    day_pattern: str
    start_time: str
    end_time: str
    status: str = "confirmed"


class SeedResponse(BaseModel):
    status: str = "seeded"
    campuses: int
    buildings: int
    rooms: int
    users: int
    courses: int
    time_slots: int
    semesters: int
    preferences: int
    schedules: int


class SolverRunRequest(BaseModel):
    semester_id: int = Field(default=1, description="Target semester ID (1..6)")
    max_courses_per_instructor: int = Field(default=2, ge=1, le=5)
    min_courses_per_instructor: int = Field(default=1, ge=0, le=5)
    enforce_zero_violations: bool = Field(
        default=False,
        description=(
            "If true, forces an infeasible (over-constrained) run to exercise AC 2.3"
        ),
    )


class SolverRunResponse(BaseModel):
    status: str
    semester_id: int
    scheduled_count: int
    wall_time_seconds: float
    satisfaction_rate: float


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    department: str
    priority_score: int


class SemesterResponse(BaseModel):
    id: int
    semester_id: int
    name: str
    start_date: str
    end_date: str
    is_active: bool


class InstructorPriorityDelta(BaseModel):
    user_id: int
    instructor_name: str
    old_priority: int
    new_priority: int
    delta: int
    satisfaction_rate: Optional[float] = None


class SemesterSimulationResult(BaseModel):
    semester_id: int
    semester_name: str
    status: str
    scheduled_count: int
    wall_time_seconds: float
    satisfaction_rate: float
    priority_updates: List[InstructorPriorityDelta] = Field(default_factory=list)


class MultiSemesterSimulationRequest(BaseModel):
    semester_ids: List[int] = Field(
        default=[1, 2, 3, 4, 5, 6],
        min_length=1,
        description="Ordered list of semester IDs to simulate sequentially",
    )
    max_courses_per_instructor: int = Field(default=2, ge=1, le=5)
    min_courses_per_instructor: int = Field(default=1, ge=0, le=5)
    reset_priorities_before_run: bool = Field(
        default=True,
        description="Reset instructor priorities to base 100,000 before simulation",
    )


class MultiSemesterSimulationResponse(BaseModel):
    semesters_simulated: int
    total_scheduled_events: int
    average_satisfaction_rate: float
    total_wall_time_seconds: float
    results: List[SemesterSimulationResult]
    final_priorities: Dict[str, int]


class ScheduleCreateRequest(BaseModel):
    semester_id: int
    course_id: int
    user_id: int
    room_id: int
    time_slot_id: int
    status: str = "confirmed"


class ScheduleOverrideRequest(BaseModel):
    room_id: Optional[int] = None
    time_slot_id: Optional[int] = None
    user_id: Optional[int] = None
    status: Optional[str] = None


class EditRequestCreate(BaseModel):
    schedule_id: int
    requester_id: int
    requested_changes: str = Field(..., min_length=3, max_length=1000)
    proposed_room_id: Optional[int] = None
    proposed_time_slot_id: Optional[int] = None


class EditRequestReview(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    reviewer_notes: Optional[str] = None


class EditRequestResponse(BaseModel):
    id: int
    schedule_id: int
    requester_id: int
    requested_changes: str
    proposed_room_id: Optional[int] = None
    proposed_time_slot_id: Optional[int] = None
    reviewer_notes: Optional[str] = None
    status: str
    created_at: Optional[str] = None


class LoginRequest(BaseModel):
    identifier: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    password: str


class AuthUserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    department: str
    linked_user_id: Optional[int] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    session_id: str
    expires_at: str
    user: AuthUserResponse


class SessionMeResponse(BaseModel):
    session_id: str
    expires_at: str
    user: AuthUserResponse


class LogoutResponse(BaseModel):
    status: str = "logged_out"
    revoked_session_id: str


class DemoAccountResponse(BaseModel):
    email: str
    username: str
    full_name: str
    role: str
    department: str
    password: str
    linked_user_id: Optional[int] = None
