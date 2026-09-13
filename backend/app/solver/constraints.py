from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HardConstraint:
    """Represents a non-negotiable rule that the CP-SAT solver must satisfy."""
    name: str
    description: str
    is_satisfied: bool = True
    violation_count: int = 0
    details: List[str] = field(default_factory=list)


@dataclass
class SoftConstraint:
    """Represents an optimization objective with priority weight."""
    name: str
    description: str
    weight: int
    dimension: str  # "day", "slot", "room"
    fulfillment_rate: float = 0.0


# Standard Constraints in OptiSched
HARD_CONSTRAINTS = [
    HardConstraint(
        name="RoomCapacity",
        description="Course expected enrollment must not exceed assigned classroom capacity.",
    ),
    HardConstraint(
        name="InstructorConflict",
        description="An instructor cannot be scheduled in two courses at the same day and time.",
    ),
    HardConstraint(
        name="RoomConflict",
        description="A classroom cannot be assigned to two courses at the same day and time.",
    ),
    HardConstraint(
        name="MaxCoursesPerInstructor",
        description="An instructor cannot teach more than 2 courses in any single semester.",
    ),
    HardConstraint(
        name="CourseQualification",
        description="An instructor must be qualified (teach within their domain) for assigned courses.",
    ),
    HardConstraint(
        name="LabLayoutRequirement",
        description="Courses marked requires_lab must be scheduled in designated lab rooms.",
    ),
]

SOFT_CONSTRAINTS = [
    SoftConstraint(
        name="PreferredDays",
        description="Maximize scheduling on instructor preferred days of the week.",
        weight=2,  # per meeting day (max 4 pts = 40%)
        dimension="day",
    ),
    SoftConstraint(
        name="PreferredTimeSlot",
        description="Maximize assignment to instructor preferred time slots.",
        weight=4,  # max 4 pts = 40%
        dimension="slot",
    ),
    SoftConstraint(
        name="PreferredClassroom",
        description="Maximize assignment to instructor preferred classrooms and layout types.",
        weight=2,  # max 2 pts = 20%
        dimension="room",
    ),
]
