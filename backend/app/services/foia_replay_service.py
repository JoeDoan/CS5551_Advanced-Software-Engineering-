"""Two-stage non-circular UIUC FOIA empirical benchmark (Spring 2026 held-out).

Stage 1 forecasts Spring 2026 enrollment across 40 STEM courses from the 19
observed FOIA terms (Fall 2016 .. Fall 2025) without exposing Spring 2026 rows.
Stage 2 solves three pre-semester CP-SAT room-sizing schedules from causal
inputs only, then evaluates room overflows, seat utilization, empty-seat waste,
midday concentration, and 2-year habit continuity against held-out Spring 2026
UIUC registrar ground truth.
"""

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Tuple

from fastapi import HTTPException, status
from ortools.sat.python import cp_model
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.seeder import get_default_data_dir
from app.models.entities import Course, EnrollmentObservation
from app.services.forecast_service import (
    CourseForecast,
    EnrollmentForecastResponse,
    get_enrollment_forecast,
)
from app.solver.data_loader import DataLoader
from app.solver.engine import DATE, build_schedule_model, load_profiles_from_data

DATASET_SOURCE = "UIUC FOIA Registrar & Course Explorer 2016-2026"
PREFERENCE_PROVENANCE = (
    "Causal 2-year modal per (instructor, course); "
    "unrecorded pairs left with no preference"
)
HELDOUT_SEMESTER_ID = 6
HELDOUT_FILENAME = "heldout_spring2026_ground_truth.json"

_DAY_ABBR = {
    "Monday": "M",
    "Tuesday": "T",
    "Wednesday": "W",
    "Thursday": "R",
    "Friday": "F",
}

_STATUS_NAMES = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


class ForecastBenchmarkSummary(BaseModel):
    champion_model: str
    last_term_copy_naive_mae: float
    last_term_copy_naive_smape_pct: float
    champion_mae: float
    champion_smape_pct: float
    mae_reduction_vs_last_term_pct: float
    empirical_coverage_80: float
    empirical_coverage_95: float


class ScheduleBenchmarkSummary(BaseModel):
    solver_status: str
    hard_conflicts: int
    overflow_courses_last_term_sizing: int
    overflow_courses_point_forecast_sizing: int
    overflow_courses_conformal_80_sizing: int
    uiuc_actual_seat_utilization_pct: float
    optisched_seat_utilization_pct: float
    uiuc_empty_seat_waste_pct: float
    optisched_empty_seat_waste_pct: float
    uiuc_midday_concentration_pct: float
    optisched_midday_concentration_pct: float
    habit_continuity_on_pref_courses_pct: float


class CourseBenchmarkComparison(BaseModel):
    course_code: str
    course_name: str
    department: str
    has_2yr_preference: bool
    fall_2025_enrolled: int
    predicted_enrollment: float
    actual_enrollment: int
    abs_error: float
    interval_80: Tuple[float, float]
    within_80: bool
    optisched_room: str
    optisched_room_capacity: int
    optisched_slot: str
    uiuc_actual_room: str
    uiuc_actual_room_capacity: int
    uiuc_actual_slot: str


class EmpiricalBenchmarkResponse(BaseModel):
    dataset_source: str
    heldout_semester_id: int
    heldout_semester_name: str
    observed_semesters_count: int
    evaluated_courses_count: int
    courses_with_2yr_habit_pref: int
    courses_without_pref: int
    preference_provenance: str
    forecast_benchmark: ForecastBenchmarkSummary
    schedule_benchmark: ScheduleBenchmarkSummary
    course_comparisons: List[CourseBenchmarkComparison]


@dataclass(frozen=True)
class _ScheduledSection:
    course_code: str
    course_name: str
    instructor: str
    room: str
    room_capacity: int
    slot_id: int
    days: Tuple[str, ...]
    slot_label: str
    slot_display: str
    is_midday: bool


@dataclass(frozen=True)
class _CausalSizingDecisions:
    solver_status: str
    hard_conflicts: int
    courses_with_2yr_habit_pref: int
    courses_without_pref: int
    pref_course_codes: FrozenSet[str]
    habit_continuity_on_pref_courses_pct: float
    midday_concentration_pct: float
    last_term_sections: Dict[str, _ScheduledSection]
    point_forecast_sections: Dict[str, _ScheduledSection]
    conformal_80_sections: Dict[str, _ScheduledSection]


_BENCHMARK_CACHE: Dict[Tuple[Any, ...], EmpiricalBenchmarkResponse] = {}


def _canonicalize_objective(model: cp_model.CpModel) -> None:
    """Sort and merge objective terms by variable index so set-iteration order
    inside build_schedule_model cannot vary across PYTHONHASHSEED runs.
    """
    obj_proto = model.Proto().objective
    if not obj_proto.vars:
        return
    agg: Dict[int, int] = {}
    for var_idx, coeff in zip(obj_proto.vars, obj_proto.coeffs):
        agg[int(var_idx)] = agg.get(int(var_idx), 0) + int(coeff)
    sorted_vars = sorted(idx for idx, val in agg.items() if val != 0)
    obj_proto.vars.clear()
    obj_proto.coeffs.clear()
    obj_proto.vars.extend(sorted_vars)
    obj_proto.coeffs.extend(agg[idx] for idx in sorted_vars)


def _course_requires_lab(course: Dict[str, Any]) -> bool:
    return bool(course.get("requires_lab")) or (
        str(course.get("required_layout", "")).lower() == "lab"
    )


def _solve_sizing_mode(
    loader: DataLoader,
    base_profiles: Dict[str, Any],
    target_caps_by_name: Dict[str, int],
    course_code_by_name: Dict[str, str],
) -> Tuple[str, int, Dict[str, _ScheduledSection]]:
    instructors = sorted(u["name"] for u in loader.get_instructors())
    courses = sorted(c["course_name"] for c in loader.courses)
    class_room = sorted(r["room_number"] for r in loader.rooms)
    ordered_slots = sorted(loader.time_slots, key=lambda ts: ts["slot_id"])
    slots = {
        ts["slot_id"]: f"{ts['start_time']} - {ts['end_time']}"
        for ts in ordered_slots
    }
    slot_bounds = {
        ts["slot_id"]: (ts["start_time"], ts["end_time"]) for ts in ordered_slots
    }
    room_caps = {r["room_number"]: int(r["capacity"]) for r in loader.rooms}
    room_layouts = {
        r["room_number"]: r.get("layout_type", "lecture") for r in loader.rooms
    }
    req_lab_by_name = {
        c["course_name"]: _course_requires_lab(c) for c in loader.courses
    }

    # Preserve 100% of 2-year day/slot habits while filtering historical
    # oversized auditorium IDs (>1.35x target_cap) and lecture-only layout tags
    # that would otherwise outrank tight-fit packing by W_i >= 100,000.
    profiles = copy.deepcopy(base_profiles)
    right_sized_pref_rooms: Dict[str, set[str]] = {}
    for prof in profiles.values():
        prof["preferences"]["classrooms"] = []
        prof["preferences"]["layout"] = None
        for cname, cp in prof["course_preferences"].items():
            tcap = target_caps_by_name[cname]
            kept_rooms = [
                r
                for r in cp["classrooms"]
                if room_caps.get(r, 999) <= int(tcap * 1.35)
            ]
            cp["classrooms"] = kept_rooms
            cp["layout"] = "lab" if req_lab_by_name.get(cname, False) else None
            if kept_rooms:
                right_sized_pref_rooms.setdefault(cname, set()).update(kept_rooms)

    inst_by_id = {u["user_id"]: u["name"] for u in loader.get_instructors()}
    cname_by_id = {c["course_id"]: c["course_name"] for c in loader.courses}
    sem_ic_pairs = {
        (inst_by_id[p["instructor_id"]], cname_by_id[p["course_id"]])
        for p in loader.instructor_preferences
        if p.get("semester_id") == HELDOUT_SEMESTER_ID
        and p.get("instructor_id") in inst_by_id
        and p.get("course_id") in cname_by_id
    }
    valid_ic_pairs = sorted(sem_ic_pairs or loader.get_valid_ic_pairs())

    valid_rc_pairs: set[Tuple[str, str]] = set()
    for course in loader.courses:
        cname = course["course_name"]
        tcap = target_caps_by_name[cname]
        req_lab = req_lab_by_name[cname]
        compat = sorted(
            [
                r
                for r in loader.rooms
                if (not req_lab or r.get("layout_type") == "lab")
                and int(r["capacity"]) >= tcap
            ],
            key=lambda r: (int(r["capacity"]), int(r["room_id"])),
        )
        compat_nums = {r["room_number"] for r in compat}
        chosen = {r["room_number"] for r in compat[:6]}
        chosen.update(right_sized_pref_rooms.get(cname, set()) & compat_nums)
        for rnum in chosen:
            valid_rc_pairs.add((rnum, cname))

    # Assortative ratio term breaks permutation symmetry across equal-sum room
    # assignments while staying <= 440 per course (40 * 440 << W_i >= 100,000).
    y_bonus: Dict[Tuple[str, int, str, str], int] = {}
    for inst_name, cname in valid_ic_pairs:
        tcap = target_caps_by_name[cname]
        for rnum in class_room:
            if (rnum, cname) not in valid_rc_pairs:
                continue
            rcap = room_caps[rnum]
            pack = max(0, 200 - (rcap - tcap)) + int(
                round(200.0 * tcap / max(1, rcap))
            )
            for sid in slots:
                start_time = slot_bounds[sid][0]
                off_peak = 0 if ("10:00" <= start_time <= "13:59") else 40
                y_bonus[(rnum, sid, inst_name, cname)] = pack + off_peak

    model, X, Y, _Z, _weights = build_schedule_model(
        profiles=profiles,
        date=DATE,
        class_room=class_room,
        instructors=instructors,
        courses=courses,
        slots=slots,
        seed=42,
        room_capacities=room_caps,
        course_enrollments=target_caps_by_name,
        room_layouts=room_layouts,
        valid_ic_pairs=valid_ic_pairs,
        valid_rc_pairs=valid_rc_pairs,
        y_bonus=y_bonus,
    )

    # Exact facet description of valid 2-day academic patterns {MW, TR, WF}
    # eliminates auxiliary pattern booleans from branch-and-bound.
    for rnum, sid, inst_name, cname in sorted(Y.keys()):
        y_var = Y[rnum, sid, inst_name, cname]
        model.Add(
            X["Tuesday", rnum, sid, inst_name, cname]
            == X["Thursday", rnum, sid, inst_name, cname]
        )
        model.Add(
            X["Monday", rnum, sid, inst_name, cname]
            + X["Friday", rnum, sid, inst_name, cname]
            == X["Wednesday", rnum, sid, inst_name, cname]
        )
        model.Add(
            X["Wednesday", rnum, sid, inst_name, cname]
            + X["Tuesday", rnum, sid, inst_name, cname]
            == y_var
        )

    _canonicalize_objective(model)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 42
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = 10.0

    raw_status = solver.Solve(model)
    status_name = _STATUS_NAMES.get(raw_status, "UNKNOWN")
    if raw_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"CP-SAT benchmark solve failed with status {status_name}")

    sections_by_code: Dict[str, _ScheduledSection] = {}
    room_meetings: set[Tuple[str, int, str]] = set()
    inst_meetings: set[Tuple[str, int, str]] = set()
    hard_conflicts = 0

    for rnum, sid, inst_name, cname in sorted(Y.keys()):
        if not solver.Value(Y[rnum, sid, inst_name, cname]):
            continue
        active_days = tuple(
            day
            for day in DATE
            if solver.Value(X[day, rnum, sid, inst_name, cname])
        )
        for day in active_days:
            rk = (day, sid, rnum)
            ik = (day, sid, inst_name)
            if rk in room_meetings:
                hard_conflicts += 1
            if ik in inst_meetings:
                hard_conflicts += 1
            room_meetings.add(rk)
            inst_meetings.add(ik)

        start_time, end_time = slot_bounds[sid]
        day_code = "".join(_DAY_ABBR[day] for day in active_days)
        ccode = course_code_by_name[cname]
        sections_by_code[ccode] = _ScheduledSection(
            course_code=ccode,
            course_name=cname,
            instructor=inst_name,
            room=rnum,
            room_capacity=room_caps[rnum],
            slot_id=sid,
            days=active_days,
            slot_label=slots[sid],
            slot_display=f"{day_code} {start_time}-{end_time}",
            is_midday=("10:00" <= start_time <= "13:59"),
        )

    return status_name, hard_conflicts, sections_by_code


def _build_causal_decisions(
    forecast_resp: EnrollmentForecastResponse,
    data_dir: Path,
) -> _CausalSizingDecisions:
    loader = DataLoader(data_dir=str(data_dir))
    base_profiles = load_profiles_from_data(
        loader, semester_id=HELDOUT_SEMESTER_ID
    )

    fc_by_id: Dict[int, CourseForecast] = {
        fc.course_id: fc for fc in forecast_resp.courses
    }
    course_code_by_id: Dict[int, str] = {
        fc.course_id: fc.course_code for fc in forecast_resp.courses
    }
    course_code_by_name: Dict[str, str] = {
        c["course_name"]: course_code_by_id[int(c["course_id"])]
        for c in loader.courses
    }

    last_term_caps: Dict[str, int] = {}
    point_forecast_caps: Dict[str, int] = {}
    conformal_80_caps: Dict[str, int] = {}

    for course in loader.courses:
        cid = int(course["course_id"])
        cname = course["course_name"]
        req_lab = _course_requires_lab(course)
        max_compat_cap = max(
            int(r["capacity"])
            for r in loader.rooms
            if not req_lab or r.get("layout_type") == "lab"
        )
        fc = fc_by_id[cid]
        fall_2025_enrolled = int(fc.history[-1].enrolled)
        last_term_caps[cname] = min(
            max_compat_cap, max(1, math.ceil(fall_2025_enrolled * 1.05))
        )
        point_forecast_caps[cname] = min(
            max_compat_cap, max(1, math.ceil(fc.forecast * 1.05))
        )
        conformal_80_caps[cname] = min(
            max_compat_cap, max(1, math.ceil(fc.interval_80[1]))
        )

    _lt_status, _lt_conf, lt_sections = _solve_sizing_mode(
        loader, base_profiles, last_term_caps, course_code_by_name
    )
    _pf_status, _pf_conf, pf_sections = _solve_sizing_mode(
        loader, base_profiles, point_forecast_caps, course_code_by_name
    )
    c80_status, c80_conf, c80_sections = _solve_sizing_mode(
        loader, base_profiles, conformal_80_caps, course_code_by_name
    )

    pref_specs: Dict[str, Tuple[set[str], set[Any]]] = {}
    without_pref_count = 0
    for pref in loader.instructor_preferences:
        if pref.get("semester_id") != HELDOUT_SEMESTER_ID:
            continue
        cid = pref.get("course_id")
        if cid is None or int(cid) not in course_code_by_id:
            continue
        resolved = loader.get_resolved_preference(
            pref["instructor_id"],
            course_id=int(cid),
            semester_id=HELDOUT_SEMESTER_ID,
        )
        ccode = course_code_by_id[int(cid)]
        if resolved["has_preferences"]:
            pref_specs[ccode] = (set(resolved["days"]), set(resolved["slots"]))
        else:
            without_pref_count += 1

    habit_matches = 0
    for ccode, (pref_days, pref_slots) in pref_specs.items():
        sec = c80_sections[ccode]
        days_ok = bool(pref_days) and set(sec.days).issubset(pref_days)
        slot_ok = bool(pref_slots) and (
            (sec.slot_id in pref_slots) or (sec.slot_label in pref_slots)
        )
        if days_ok and slot_ok:
            habit_matches += 1

    with_pref_count = len(pref_specs)
    habit_pct = (
        round(100.0 * habit_matches / with_pref_count, 1)
        if with_pref_count
        else 0.0
    )
    midday_pct = round(
        100.0
        * sum(1 for sec in c80_sections.values() if sec.is_midday)
        / max(1, len(c80_sections)),
        1,
    )

    return _CausalSizingDecisions(
        solver_status=c80_status,
        hard_conflicts=c80_conf,
        courses_with_2yr_habit_pref=with_pref_count,
        courses_without_pref=without_pref_count,
        pref_course_codes=frozenset(pref_specs.keys()),
        habit_continuity_on_pref_courses_pct=habit_pct,
        midday_concentration_pct=midday_pct,
        last_term_sections=lt_sections,
        point_forecast_sections=pf_sections,
        conformal_80_sections=c80_sections,
    )


def _smape_pct(actual: float, pred: float) -> float:
    return 200.0 * abs(actual - pred) / max(1e-9, abs(actual) + abs(pred))


def _evaluate_against_heldout(
    forecast_resp: EnrollmentForecastResponse,
    decisions: _CausalSizingDecisions,
    heldout: Dict[str, Any],
) -> EmpiricalBenchmarkResponse:
    fc_by_code = {fc.course_code: fc for fc in forecast_resp.courses}
    audit = heldout["campus_wide_2026sp_audit"]
    gt_courses = heldout["courses"]

    naive_errs: List[float] = []
    naive_smapes: List[float] = []
    champ_errs: List[float] = []
    champ_smapes: List[float] = []
    within_80_count = 0
    within_95_count = 0

    overflow_lt = 0
    overflow_pf = 0
    overflow_c80 = 0
    occupied_seats = 0
    empty_seats = 0
    total_assigned_seats = 0

    comparisons: List[CourseBenchmarkComparison] = []

    for gt in gt_courses:
        ccode = gt["course_code"]
        fc = fc_by_code[ccode]
        fall_2025 = int(fc.history[-1].enrolled)
        actual = int(gt["actual_spring_2026_enrolled"])
        pred = round(float(fc.forecast), 1)
        abs_err = round(abs(actual - float(fc.forecast)), 1)

        naive_errs.append(abs(actual - fall_2025))
        naive_smapes.append(_smape_pct(actual, fall_2025))
        champ_errs.append(abs(actual - float(fc.forecast)))
        champ_smapes.append(_smape_pct(actual, float(fc.forecast)))

        in_80 = bool(fc.interval_80[0] <= actual <= fc.interval_80[1])
        in_95 = bool(fc.interval_95[0] <= actual <= fc.interval_95[1])
        if in_80:
            within_80_count += 1
        if in_95:
            within_95_count += 1

        if decisions.last_term_sections[ccode].room_capacity < actual:
            overflow_lt += 1
        if decisions.point_forecast_sections[ccode].room_capacity < actual:
            overflow_pf += 1

        c80_sec = decisions.conformal_80_sections[ccode]
        if c80_sec.room_capacity < actual:
            overflow_c80 += 1

        occupied_seats += min(actual, c80_sec.room_capacity)
        empty_seats += max(0, c80_sec.room_capacity - actual)
        total_assigned_seats += c80_sec.room_capacity

        bldg = (gt.get("uiuc_actual_building") or "").strip()
        rm_num = (gt.get("uiuc_actual_room") or "").strip()
        uiuc_room = f"{bldg} {rm_num}".strip() or "Arranged"
        raw_uiuc_cap = gt.get("uiuc_actual_room_capacity")
        uiuc_cap = int(raw_uiuc_cap) if raw_uiuc_cap is not None else actual
        uiuc_days = (gt.get("uiuc_actual_days") or "").strip()
        uiuc_start = (gt.get("uiuc_actual_start_time") or "").strip()
        uiuc_end = (gt.get("uiuc_actual_end_time") or "").strip()
        uiuc_slot = (
            f"{uiuc_days} {uiuc_start}-{uiuc_end}".strip()
            if (uiuc_days and uiuc_start and uiuc_end)
            else (uiuc_days or "Arranged")
        )

        comparisons.append(
            CourseBenchmarkComparison(
                course_code=ccode,
                course_name=fc.course_name,
                department=fc.department,
                has_2yr_preference=(ccode in decisions.pref_course_codes),
                fall_2025_enrolled=fall_2025,
                predicted_enrollment=pred,
                actual_enrollment=actual,
                abs_error=abs_err,
                interval_80=(
                    round(float(fc.interval_80[0]), 1),
                    round(float(fc.interval_80[1]), 1),
                ),
                within_80=in_80,
                optisched_room=c80_sec.room,
                optisched_room_capacity=c80_sec.room_capacity,
                optisched_slot=c80_sec.slot_display,
                uiuc_actual_room=uiuc_room,
                uiuc_actual_room_capacity=uiuc_cap,
                uiuc_actual_slot=uiuc_slot,
            )
        )

    n_courses = max(1, len(gt_courses))
    naive_mae = sum(naive_errs) / n_courses
    champ_mae = sum(champ_errs) / n_courses
    mae_reduction = 100.0 * (1.0 - champ_mae / max(1e-9, naive_mae))

    forecast_summary = ForecastBenchmarkSummary(
        champion_model=forecast_resp.meta.champion_model,
        last_term_copy_naive_mae=round(naive_mae, 2),
        last_term_copy_naive_smape_pct=round(sum(naive_smapes) / n_courses, 2),
        champion_mae=round(champ_mae, 2),
        champion_smape_pct=round(sum(champ_smapes) / n_courses, 2),
        mae_reduction_vs_last_term_pct=round(mae_reduction, 1),
        empirical_coverage_80=round(within_80_count / n_courses, 4),
        empirical_coverage_95=round(within_95_count / n_courses, 4),
    )

    denom_seats = max(1, total_assigned_seats)
    schedule_summary = ScheduleBenchmarkSummary(
        solver_status=decisions.solver_status,
        hard_conflicts=decisions.hard_conflicts,
        overflow_courses_last_term_sizing=overflow_lt,
        overflow_courses_point_forecast_sizing=overflow_pf,
        overflow_courses_conformal_80_sizing=overflow_c80,
        uiuc_actual_seat_utilization_pct=round(
            float(audit["mean_seat_utilization_pct"]), 1
        ),
        optisched_seat_utilization_pct=round(
            100.0 * occupied_seats / denom_seats, 1
        ),
        uiuc_empty_seat_waste_pct=round(
            float(audit["empty_seat_waste_pct"]), 1
        ),
        optisched_empty_seat_waste_pct=round(
            100.0 * empty_seats / denom_seats, 1
        ),
        uiuc_midday_concentration_pct=round(
            float(audit["midday_10am_2pm_concentration_pct"]), 1
        ),
        optisched_midday_concentration_pct=decisions.midday_concentration_pct,
        habit_continuity_on_pref_courses_pct=(
            decisions.habit_continuity_on_pref_courses_pct
        ),
    )

    return EmpiricalBenchmarkResponse(
        dataset_source=DATASET_SOURCE,
        heldout_semester_id=int(heldout["heldout_semester_id"]),
        heldout_semester_name=str(heldout["heldout_semester_name"]),
        observed_semesters_count=len(forecast_resp.meta.observed_semester_ids),
        evaluated_courses_count=len(comparisons),
        courses_with_2yr_habit_pref=decisions.courses_with_2yr_habit_pref,
        courses_without_pref=decisions.courses_without_pref,
        preference_provenance=PREFERENCE_PROVENANCE,
        forecast_benchmark=forecast_summary,
        schedule_benchmark=schedule_summary,
        course_comparisons=comparisons,
    )


def get_empirical_benchmark(session: Session) -> EmpiricalBenchmarkResponse:
    data_dir = Path(get_default_data_dir())
    heldout_path = data_dir / HELDOUT_FILENAME
    if not heldout_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Empirical benchmark ground truth is not available "
                "for the active data profile."
            ),
        )

    obs_count, sum_enrolled = session.exec(
        select(
            func.count(EnrollmentObservation.id),
            func.coalesce(func.sum(EnrollmentObservation.enrolled), 0),
        ).where(EnrollmentObservation.semester_id != HELDOUT_SEMESTER_ID)
    ).one()
    course_count = session.exec(select(func.count(Course.id))).one()
    cache_key = (
        str(heldout_path.resolve()),
        heldout_path.stat().st_mtime_ns,
        int(obs_count),
        int(sum_enrolled),
        int(course_count),
    )
    cached = _BENCHMARK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    forecast_resp = get_enrollment_forecast(
        session=session, semester_id=HELDOUT_SEMESTER_ID
    )
    decisions = _build_causal_decisions(forecast_resp, data_dir)
    heldout = json.loads(heldout_path.read_text(encoding="utf-8"))
    result = _evaluate_against_heldout(forecast_resp, decisions, heldout)
    _BENCHMARK_CACHE[cache_key] = result
    return result
