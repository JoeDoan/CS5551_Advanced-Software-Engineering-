"""Dry-run what-if scenarios on top of the CP-SAT scheduler.

Nothing here persists anything: every run builds a fresh in-memory ``DataLoader``
(never calling its ``save_*`` methods), reads SQLite preferences/assignments
read-only and returns metrics. The baseline (no modifications) and the scenario
use the same seed, worker count and time limit so their difference is the effect
of the scenario. The scenario run also gets a small reward for keeping baseline
placements so the diff shows a minimum-disruption re-solve, not a reshuffle.
"""

import hashlib
import json
import math
import os
import threading
from typing import Dict, List, Literal, Optional, Set, Tuple

from fastapi import HTTPException
from ortools.sat.python import cp_model
from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session, select

from app.models.entities import (
    InstructorCourseAssignment,
    InstructorPreference,
    Semester,
)
from app.services.analytics_service import _compute_gini
from app.services.forecast_service import run_pipeline
from app.services.solver_service import (
    _overlay_sqlite_preferences,
    _resolve_pinned_assignments,
)
from app.solver.data_loader import DataLoader
from app.solver.engine import (
    BASE_PRIORITY,
    DATE,
    build_schedule_model,
    evaluate_satisfaction_and_update,
    get_metadata,
    load_profiles_from_data,
)

ADJUNCT_NAME = "Adjunct Faculty (Grant Buyout Replacement)"
# Reward per baseline placement that is kept. "minimal" dominates any preference gain from a
# single course (about 1e6), so only forced changes happen; "reoptimize" is a pure tie-break.
STABILITY_WEIGHTS = {"minimal": 5_000_000, "reoptimize": 25}
SOLVER_WORKERS = max(1, int(os.getenv("SCENARIO_SOLVER_WORKERS", str(min(8, os.cpu_count() or 4)))))
BASELINE_TIME_LIMIT_SECONDS = float(os.getenv("SCENARIO_BASELINE_TIME_LIMIT", "60"))
GAP_LIMIT = float(os.getenv("SCENARIO_GAP_LIMIT", "0.005"))  # stop once within 0.5% of the bound
LOCK_TIMEOUT_SECONDS = 120
DATA_FILES = (
    "users.json",
    "courses.json",
    "rooms.json",
    "time_slots.json",
    "instructor_preferences.json",
)

_SOLVE_LOCK = threading.Lock()
_BASELINE_CACHE: Dict[tuple, "ScenarioMetrics"] = {}
_CACHE_LIMIT = 16


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class EnrollmentGrowth(BaseModel):
    department: str = Field(min_length=2, max_length=10)
    pct: float = Field(ge=-50, le=100)


class BuyoutSpec(BaseModel):
    instructor: str = Field(min_length=3, max_length=80)
    max_courses: int = Field(default=1, ge=1, le=2)
    reason: Optional[str] = Field(default=None, max_length=120)


class RoomSlotBlock(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    slot_id: int = Field(ge=1)
    reason: Optional[str] = Field(default=None, max_length=120)


class ScenarioSpec(BaseModel):
    semester_id: int = 6
    use_forecast: bool = False
    enrollment_growth: List[EnrollmentGrowth] = Field(default_factory=list, max_length=10)
    buyouts: List[BuyoutSpec] = Field(default_factory=list, max_length=5)
    coverage_strategy: Literal["none", "overload", "adjunct"] = "overload"
    room_capacity_scale: float = Field(default=1.0, ge=0.5, le=2.0)
    blocked_room_slots: List[RoomSlotBlock] = Field(default_factory=list, max_length=10)
    max_courses_per_instructor: int = Field(default=2, ge=1, le=5)
    min_courses_per_instructor: int = Field(default=1, ge=0, le=5)
    change_policy: Literal["minimal", "reoptimize"] = "minimal"
    time_limit_seconds: float = Field(default=10.0, ge=1.0, le=30.0)
    seed: int = 5551

    @model_validator(mode="after")
    def _check(self):
        names = [b.instructor.strip().lower() for b in self.buyouts]
        if len(names) != len(set(names)):
            raise ValueError("Each instructor can appear in at most one buyout.")
        if self.min_courses_per_instructor > self.max_courses_per_instructor:
            raise ValueError("min_courses_per_instructor cannot exceed the maximum.")
        for b in self.buyouts:
            if b.max_courses > self.max_courses_per_instructor:
                raise ValueError("A buyout cap cannot exceed the normal teaching load.")
        return self


class AssignmentRow(BaseModel):
    course: str
    instructors: List[str]
    room: str
    slot_id: int
    days: List[str]


class ScenarioMetrics(BaseModel):
    status: str
    wall_time_seconds: float = 0.0
    optimality_gap_pct: Optional[float] = None
    scheduled_courses: int = 0
    avg_satisfaction_pct: Optional[float] = None
    min_satisfaction_pct: Optional[float] = None
    satisfaction_gini: Optional[float] = None
    workload_gini: Optional[float] = None
    slot_utilization_pct: Optional[float] = None
    seat_occupancy_pct: Optional[float] = None
    rooms_used: int = 0
    instructor_loads: Dict[str, int] = Field(default_factory=dict)
    satisfaction_by_instructor: Dict[str, float] = Field(default_factory=dict)
    assignments: List[AssignmentRow] = Field(default_factory=list)
    diagnosis: List[str] = Field(default_factory=list)


class CourseChange(BaseModel):
    course: str
    instructors_before: List[str]
    instructors_after: List[str]
    room_before: str
    room_after: str
    slot_before: int
    slot_after: int


class ScenarioDiff(BaseModel):
    status_before: str
    status_after: str
    satisfaction_delta_pct: Optional[float] = None
    satisfaction_gini_delta: Optional[float] = None
    workload_gini_delta: Optional[float] = None
    slot_utilization_delta_pct: Optional[float] = None
    seat_occupancy_delta_pct: Optional[float] = None
    changed_courses: List[CourseChange] = Field(default_factory=list)
    absorbers: List[str] = Field(default_factory=list)
    released: List[str] = Field(default_factory=list)
    adjunct_sections: List[str] = Field(default_factory=list)


class ScenarioResponse(BaseModel):
    spec: ScenarioSpec
    semester_name: str
    baseline: ScenarioMetrics
    scenario: ScenarioMetrics
    diff: ScenarioDiff
    notes: List[str]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _state_signature(session: Session, data_dir: str) -> str:
    h = hashlib.sha256()
    for name in DATA_FILES:
        path = os.path.join(data_dir, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                h.update(f.read())
    prefs = session.exec(select(InstructorPreference).order_by(InstructorPreference.id)).all()
    h.update(
        json.dumps(
            [
                (p.id, p.user_id, p.semester_id, p.course_id, p.preferred_days,
                 p.preferred_slots, p.preferred_rooms)
                for p in prefs
            ],
            sort_keys=True,
            default=str,
        ).encode()
    )
    assigns = session.exec(
        select(InstructorCourseAssignment).order_by(InstructorCourseAssignment.id)
    ).all()
    h.update(json.dumps([(a.id, a.semester_id, a.user_id, a.course_id) for a in assigns]).encode())
    return h.hexdigest()


def _dept(course_name: str) -> str:
    return course_name.split()[0].upper() if course_name.split() else ""


def _resolve_semester(session: Session, semester_id: int) -> Semester:
    sem = session.exec(
        select(Semester).where((Semester.id == semester_id) | (Semester.semester_id == semester_id))
    ).first()
    if sem is None:
        raise HTTPException(status_code=404, detail=f"Semester {semester_id} does not exist")
    return sem


class _Mods:
    """Resolved modifications for one solve (empty = baseline)."""

    def __init__(self):
        self.forecast: Dict[int, float] = {}
        self.growth: List[EnrollmentGrowth] = []
        self.capacity_scale: float = 1.0
        self.buyouts: Dict[str, int] = {}
        self.strategy: str = "none"
        self.blocked: List[Tuple[str, int]] = []
        self.y_bonus: Optional[Dict[Tuple[str, int, str, str], int]] = None
        self.bonus_weight: int = 0
        self.hint: Optional[List["AssignmentRow"]] = None


def _solve(
    session: Session,
    semester: Semester,
    spec: ScenarioSpec,
    mods: _Mods,
    time_limit: Optional[float] = None,
) -> ScenarioMetrics:
    loader = DataLoader()  # fresh in-memory copy; its save_* methods are never called

    for c in loader.courses:
        if c["course_id"] in mods.forecast:
            c["expected_enrollment"] = max(1, round(mods.forecast[c["course_id"]]))
    known_depts = {_dept(c["course_name"]) for c in loader.courses}
    for g in mods.growth:
        dept = g.department.strip().upper()
        if dept not in known_depts:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown department '{g.department}'. Known: {sorted(known_depts)}",
            )
        for c in loader.courses:
            if _dept(c["course_name"]) == dept:
                c["expected_enrollment"] = max(
                    1, math.ceil(c["expected_enrollment"] * (1 + g.pct / 100.0))
                )
    if mods.capacity_scale != 1.0:
        for r in loader.rooms:
            r["capacity"] = max(1, int(r["capacity"] * mods.capacity_scale))

    profiles = load_profiles_from_data(loader, semester_id=semester.semester_id)
    valid_ic: Set[Tuple[str, str]] = set(loader.get_valid_ic_pairs())
    _overlay_sqlite_preferences(session, semester.id, profiles, valid_ic, loader)

    slots = loader.get_slots_dict()
    class_room = [r["room_number"] for r in loader.rooms]
    real_instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]
    room_caps, course_enrolls, room_layouts = get_metadata(loader)
    valid_rc = loader.get_valid_rc_pairs()

    # Pre-check: a course with no compatible room can never be scheduled.
    with_room = {c for (_r, c) in valid_rc}
    orphans = [c for c in courses if c not in with_room]
    if orphans:
        lines = []
        for c in orphans:
            lab = next(x for x in loader.courses if x["course_name"] == c).get("required_layout") == "lab"
            pool = [r for r in loader.rooms if (not lab or r.get("layout_type") == "lab")]
            best = max((r["capacity"] for r in pool), default=0)
            lines.append(
                f"{c}: expected enrollment {course_enrolls[c]} exceeds the largest "
                f"compatible room ({best} seats). Split the section or add capacity."
            )
        return ScenarioMetrics(status="INFEASIBLE", diagnosis=lines)

    lower = {n.lower(): n for n in real_instructors}
    buyout_caps: Dict[str, int] = {}
    for name, cap in mods.buyouts.items():
        resolved = lower.get(name.strip().lower())
        if resolved is None:
            raise HTTPException(status_code=422, detail=f"Unknown instructor '{name}'.")
        buyout_caps[resolved] = cap

    pinned_pairs, _assigned, _pinned_by_course, pinned_by_inst = _resolve_pinned_assignments(
        session, semester.id, loader, real_instructors, courses, valid_ic, valid_rc
    )

    instructors = list(real_instructors)
    caps: Dict[str, int] = {
        i: max(spec.max_courses_per_instructor, pinned_by_inst.get(i, 0)) for i in real_instructors
    }
    reduction = 0
    for name, cap in buyout_caps.items():
        reduction += caps[name] - cap
        caps[name] = cap

    cluster: Set[str] = set()
    if buyout_caps and mods.strategy == "overload":
        # Colleagues become qualified ONLY for the buyout instructors' own courses, and
        # only if they already teach that subject area. A broader expansion would loosen
        # qualification across the whole timetable and make the comparison unfair.
        freed = {c for (i, c) in valid_ic if i in buyout_caps}
        subject_of: Dict[str, Set[str]] = {}
        for (i, c) in valid_ic:
            if i not in buyout_caps and c.split():
                subject_of.setdefault(i, set()).add(c.split()[0])
        for i, subjects in subject_of.items():
            for c in freed:
                if c.split() and c.split()[0] in subjects and (i, c) not in valid_ic:
                    valid_ic.add((i, c))
                    cluster.add(i)
        cluster |= {i for i, subs in subject_of.items()
                    if any(c.split() and c.split()[0] in subs for c in freed)}
    elif buyout_caps and mods.strategy == "adjunct":
        instructors.append(ADJUNCT_NAME)
        for (i, c) in list(valid_ic):
            if i in buyout_caps:
                valid_ic.add((ADJUNCT_NAME, c))
        profiles[ADJUNCT_NAME] = {
            "user_id": -1,
            "base_priority": BASE_PRIORITY,
            "current_priority": BASE_PRIORITY,
            "preferences": {"days": [], "slots": [], "classrooms": [], "layout": None},
            "course_preferences": {},
        }
        caps[ADJUNCT_NAME] = max(1, reduction)

    qualified = {i for (i, _c) in valid_ic}
    total_capacity = sum(cap for i, cap in caps.items() if i in qualified)
    if mods.strategy == "overload" and buyout_caps:
        total_capacity += min(reduction, len(cluster & qualified))
    if total_capacity < len(courses):
        diag = (
            f"Teaching-load arithmetic: {len(courses)} courses each need at least one "
            f"instructor, but total instructor capacity is only {total_capacity}"
        )
        if buyout_caps:
            diag += f" after {reduction} course(s) of buyout"
        diag += ". Use coverage strategy 'overload' or 'adjunct', or raise the load cap."
        return ScenarioMetrics(status="INFEASIBLE", diagnosis=[diag])

    base_max = max([spec.max_courses_per_instructor] + list(caps.values()))
    if cluster:
        base_max = max(base_max, spec.max_courses_per_instructor + 1)

    model, X, Y, Z, _w = build_schedule_model(
        profiles, DATE, class_room, instructors, courses, slots,
        seed=spec.seed,
        room_capacities=room_caps, course_enrollments=course_enrolls, room_layouts=room_layouts,
        valid_ic_pairs=valid_ic, valid_rc_pairs=valid_rc,
        min_courses_per_instructor=spec.min_courses_per_instructor,
        max_courses_per_instructor=base_max,
        y_bonus=mods.y_bonus,
    )

    def load_of(i: str):
        return [Z[i, c] for c in courses if (i, c) in Z]

    extras = []
    for i in instructors:
        vars_i = load_of(i)
        if not vars_i:
            continue
        if i in cluster:
            extra = model.NewBoolVar(f"overload_{i}")
            extras.append(extra)
            model.Add(sum(vars_i) <= spec.max_courses_per_instructor + extra)
        elif caps.get(i, spec.max_courses_per_instructor) < base_max:
            model.Add(sum(vars_i) <= caps.get(i, spec.max_courses_per_instructor))
    if extras:
        model.Add(sum(extras) <= reduction)
    for (i, c) in pinned_pairs:
        if (i, c) in Z:
            model.Add(Z[i, c] == 1)
    blocked = set(mods.blocked)
    if blocked:
        for (r, s, i, c) in list(Y.keys()):
            if (r, s) in blocked:
                model.Add(Y[r, s, i, c] == 0)

    limit = time_limit if time_limit is not None else spec.time_limit_seconds
    if mods.hint:
        hint_y = {(a.room, a.slot_id, i, a.course) for a in mods.hint for i in a.instructors}
        hint_z = {(i, a.course) for a in mods.hint for i in a.instructors}
        hint_x = {(d, a.room, a.slot_id, i, a.course)
                  for a in mods.hint for i in a.instructors for d in a.days}
        for key, var in Y.items():
            model.AddHint(var, 1 if key in hint_y else 0)
        for key, var in Z.items():
            model.AddHint(var, 1 if key in hint_z else 0)
        for key, var in X.items():
            model.AddHint(var, 1 if key in hint_x else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limit
    # No repair_hint: with OR-Tools 9.15 it aborts the process at short time limits.
    solver.parameters.relative_gap_limit = GAP_LIMIT
    solver.parameters.random_seed = spec.seed
    solver.parameters.num_workers = SOLVER_WORKERS
    status = solver.Solve(model)
    names = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }
    status_name = names.get(status, "TIMEOUT")
    wall = round(solver.WallTime(), 3)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        why = {
            "INFEASIBLE": "CP-SAT proved that no timetable satisfies all hard constraints "
                          "with these modifications.",
            "TIMEOUT": f"No solution found within {limit:.0f}s; "
                       "raise time_limit_seconds.",
        }.get(status_name, "The model was rejected as invalid.")
        return ScenarioMetrics(status=status_name, wall_time_seconds=wall, diagnosis=[why])

    gap = None
    if status == cp_model.OPTIMAL:
        gap = 0.0
    else:
        try:
            obj, bound = solver.ObjectiveValue(), solver.BestObjectiveBound()
            kept = sum(1 for k in (mods.y_bonus or {}) if k in Y and solver.Value(Y[k]) == 1)
            preference_part = obj - mods.bonus_weight * kept
            gap = round(abs(bound - obj) / max(abs(preference_part), 1.0) * 100.0, 3)
        except Exception:
            gap = None

    report = evaluate_satisfaction_and_update(
        solver, profiles, X, Y, Z, DATE, class_room, instructors, courses, slots,
        room_layouts=room_layouts, loader=loader,
    )

    assignments: List[AssignmentRow] = []
    loads: Dict[str, int] = {i: 0 for i in instructors}
    occupancy: List[float] = []
    used_cells = 0
    rooms_used: Set[str] = set()
    for c in courses:
        chosen = [i for i in instructors if (i, c) in Z and solver.Value(Z[i, c]) == 1]
        if not chosen:
            continue
        placement = next(
            ((r, s) for i in chosen for r in class_room for s in slots
             if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1),
            None,
        )
        if placement is None:
            continue
        r, s = placement
        days = [d for d in DATE if any(
            (d, r, s, i, c) in X and solver.Value(X[d, r, s, i, c]) == 1 for i in chosen)]
        for i in chosen:
            loads[i] += 1
        assignments.append(AssignmentRow(course=c, instructors=chosen, room=r, slot_id=int(s), days=days))
        used_cells += len(days)
        rooms_used.add(r)
        occupancy.append(course_enrolls[c] / max(room_caps[r], 1))

    rates = {
        i: rep["satisfaction_rate"]
        for i, rep in report.items()
        if rep.get("has_preferences") and i != ADJUNCT_NAME
    }
    real_loads = [loads[i] for i in real_instructors]
    total_cells = len(DATE) * len(class_room) * len(slots)
    return ScenarioMetrics(
        status=status_name,
        wall_time_seconds=wall,
        optimality_gap_pct=gap,
        scheduled_courses=len(assignments),
        avg_satisfaction_pct=round(sum(rates.values()) / len(rates) * 100.0, 2) if rates else None,
        min_satisfaction_pct=round(min(rates.values()) * 100.0, 2) if rates else None,
        satisfaction_gini=_compute_gini(list(rates.values())) if len(rates) > 1 else None,
        workload_gini=_compute_gini([float(v) for v in real_loads]) if real_loads else None,
        slot_utilization_pct=round(used_cells / total_cells * 100.0, 2) if total_cells else None,
        seat_occupancy_pct=round(sum(occupancy) / len(occupancy) * 100.0, 2) if occupancy else None,
        rooms_used=len(rooms_used),
        instructor_loads={i: v for i, v in loads.items() if v},
        satisfaction_by_instructor={i: round(v * 100.0, 2) for i, v in rates.items()},
        assignments=assignments,
    )


def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else round(b - a, 3)


def _diff(base: ScenarioMetrics, scen: ScenarioMetrics) -> ScenarioDiff:
    diff = ScenarioDiff(status_before=base.status, status_after=scen.status)
    if scen.status not in ("OPTIMAL", "FEASIBLE") or base.status not in ("OPTIMAL", "FEASIBLE"):
        return diff
    diff.satisfaction_delta_pct = _delta(base.avg_satisfaction_pct, scen.avg_satisfaction_pct)
    diff.satisfaction_gini_delta = _delta(base.satisfaction_gini, scen.satisfaction_gini)
    diff.workload_gini_delta = _delta(base.workload_gini, scen.workload_gini)
    diff.slot_utilization_delta_pct = _delta(base.slot_utilization_pct, scen.slot_utilization_pct)
    diff.seat_occupancy_delta_pct = _delta(base.seat_occupancy_pct, scen.seat_occupancy_pct)
    before = {a.course: a for a in base.assignments}
    after = {a.course: a for a in scen.assignments}
    for course in sorted(set(before) | set(after)):
        b, a = before.get(course), after.get(course)
        if b is None or a is None:
            continue
        if (sorted(b.instructors), b.room, b.slot_id) != (sorted(a.instructors), a.room, a.slot_id):
            diff.changed_courses.append(CourseChange(
                course=course, instructors_before=b.instructors, instructors_after=a.instructors,
                room_before=b.room, room_after=a.room, slot_before=b.slot_id, slot_after=a.slot_id))
    names = set(base.instructor_loads) | set(scen.instructor_loads)
    for n in sorted(names):
        d = scen.instructor_loads.get(n, 0) - base.instructor_loads.get(n, 0)
        if n == ADJUNCT_NAME:
            diff.adjunct_sections = sorted(
                a.course for a in scen.assignments if ADJUNCT_NAME in a.instructors)
        elif d > 0:
            diff.absorbers.append(n)
        elif d < 0:
            diff.released.append(n)
    return diff


def simulate_scenario(session: Session, spec: ScenarioSpec) -> ScenarioResponse:
    semester = _resolve_semester(session, spec.semester_id)
    notes: List[str] = [
        "Dry run: nothing was saved. Baseline and scenario share the same seed, "
        f"solver workers ({SOLVER_WORKERS}). The baseline is solved once to near-optimality "
        f"(up to {BASELINE_TIME_LIMIT_SECONDS:.0f}s) and cached; the scenario "
        f"({spec.time_limit_seconds:.0f}s limit) is warm-started from it. Change policy "
        + (
            "'minimal': every placement the scenario does not force to change is kept."
            if spec.change_policy == "minimal"
            else "'reoptimize': the whole timetable may be rearranged to chase a better "
                 "priority-weighted score, so many unrelated courses can move."
        ),
    ]

    mods = _Mods()
    if spec.use_forecast:
        pl = run_pipeline(session, spec.semester_id)
        if pl.panel.target_sem_id != semester.id:
            raise HTTPException(
                status_code=422,
                detail=f"Forecast is only available for semester {pl.panel.target_sem_id}.",
            )
        champ = pl.forecasts[pl.champion]
        mods.forecast = {c.id: float(champ[i]) for i, c in enumerate(pl.panel.courses)}
        notes.append(
            f"Expected enrollment replaced by the '{pl.champion}' forecast"
            + (" (synthetic history)." if "synthetic" in pl.panel.sources else ".")
        )
    mods.growth = list(spec.enrollment_growth)
    mods.capacity_scale = spec.room_capacity_scale
    mods.buyouts = {b.instructor: b.max_courses for b in spec.buyouts}
    mods.strategy = spec.coverage_strategy
    mods.blocked = [(b.room_number, b.slot_id) for b in spec.blocked_room_slots]
    if spec.buyouts:
        notes.append(f"Coverage strategy for the buyout: {spec.coverage_strategy}.")
        notes.append(
            "Average satisfaction is the mean over regular faculty who have preferences. The "
            "solver maximizes a priority-weighted score, so this average can move either way; "
            "an adjunct's section carries no preferences and is not counted."
        )

    data_dir = DataLoader().data_dir
    key = (
        semester.id, spec.max_courses_per_instructor, spec.min_courses_per_instructor,
        spec.seed, BASELINE_TIME_LIMIT_SECONDS, SOLVER_WORKERS, _state_signature(session, data_dir),
    )

    if not _SOLVE_LOCK.acquire(timeout=LOCK_TIMEOUT_SECONDS):
        raise HTTPException(status_code=429, detail="Another simulation is running; try again.")
    try:
        baseline = _BASELINE_CACHE.get(key)
        if baseline is None:
            baseline = _solve(
                session, semester, spec, _Mods(), time_limit=BASELINE_TIME_LIMIT_SECONDS
            )
            if len(_BASELINE_CACHE) >= _CACHE_LIMIT:
                _BASELINE_CACHE.pop(next(iter(_BASELINE_CACHE)))
            _BASELINE_CACHE[key] = baseline
        else:
            notes.append("Baseline served from cache.")

        if baseline.status == "FEASIBLE":
            notes.append(
                f"Baseline is within {baseline.optimality_gap_pct}% of optimal, not proven "
                "optimal; differences smaller than that may be solver noise."
            )
        if baseline.status in ("OPTIMAL", "FEASIBLE"):
            mods.hint = baseline.assignments
            mods.bonus_weight = STABILITY_WEIGHTS[spec.change_policy]
            mods.y_bonus = {
                (a.room, a.slot_id, i, a.course): mods.bonus_weight
                for a in baseline.assignments for i in a.instructors
            }
        scenario = _solve(session, semester, spec, mods)
    finally:
        _SOLVE_LOCK.release()

    return ScenarioResponse(
        spec=spec,
        semester_name=semester.name,
        baseline=baseline,
        scenario=scenario,
        diff=_diff(baseline, scenario),
        notes=notes,
    )


# --------------------------------------------------------------------------
# Faculty scoping
# --------------------------------------------------------------------------
def enforce_instructor_scope(spec: ScenarioSpec, own_name: str) -> None:
    """Faculty may only simulate a buyout for themselves."""
    others = [b for b in spec.buyouts if b.instructor.strip().lower() != own_name.strip().lower()]
    if (
        not spec.buyouts
        or others
        or spec.enrollment_growth
        or spec.blocked_room_slots
        or spec.room_capacity_scale != 1.0
        or spec.use_forecast
    ):
        raise HTTPException(
            status_code=403,
            detail="Faculty can only simulate their own course buyout.",
        )


def redact_for_instructor(resp: ScenarioResponse, own_name: str) -> ScenarioResponse:
    """Hide colleagues' names and per-person satisfaction from faculty."""
    own = own_name.strip().lower()

    def mask(name: str) -> str:
        if name == ADJUNCT_NAME or name.strip().lower() == own:
            return name
        return "Colleague"

    def clean(m: ScenarioMetrics) -> ScenarioMetrics:
        out = m.model_copy(deep=True)
        out.instructor_loads = {k: v for k, v in m.instructor_loads.items()
                                if k == ADJUNCT_NAME or k.strip().lower() == own}
        out.satisfaction_by_instructor = {k: v for k, v in m.satisfaction_by_instructor.items()
                                          if k.strip().lower() == own}
        for a in out.assignments:
            a.instructors = [mask(n) for n in a.instructors]
        return out

    out = resp.model_copy(deep=True)
    out.baseline, out.scenario = clean(resp.baseline), clean(resp.scenario)
    out.diff.absorbers = ["Colleague"] * len(resp.diff.absorbers)
    out.diff.released = [n for n in resp.diff.released if n.strip().lower() == own]
    for ch in out.diff.changed_courses:
        ch.instructors_before = [mask(n) for n in ch.instructors_before]
        ch.instructors_after = [mask(n) for n in ch.instructors_after]
    return out
