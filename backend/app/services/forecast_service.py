"""Enrollment demand forecasting and room-capacity bottleneck analysis.

Pipeline (numpy only, no heavy ML dependencies):
  1. Build a course x semester panel from ``EnrollmentObservation`` rows.
  2. Fit three models and score them with a rolling-origin backtest:
       - seasonal_naive : same-season value two terms ago
       - damped_trend   : pooled season index + per-course damped Holt trend
       - pooled_ridge   : closed-form ridge on log-growth with department,
                          season, momentum, waitlist and course-level features
  3. Pick the champion by pooled backtest MAE, refit on all observed terms and
     forecast the next term.
  4. Split-conformal intervals use the champion's *relative* backtest
     residuals, which also give an empirical P(enrollment > room capacity).
  5. The capacity cliff (max compatible room capacity / enrollment - 1) is
     deterministic arithmetic, reported next to the ML forecast.

Important: with the bundled data the history is synthetic, so the backtest
validates the pipeline, not real-world accuracy. Responses say so explicitly.
"""

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.entities import Course, EnrollmentObservation, Room, Semester

MODEL_NAMES = ("seasonal_naive", "damped_trend", "pooled_ridge")
RIDGE_LAMBDA = 2.0
MIN_OBSERVED_SEMESTERS = 4
LARGE_HALL_THRESHOLDS = (100, 60, 30)
RISK_ORDER = {"critical": 0, "high": 1, "watch": 2, "ok": 3}

METHODOLOGY = (
    "Train on all observed semesters, score with a rolling-origin backtest "
    "(each origin forecasts the next term), pick the champion by pooled MAE, "
    "refit on all observed terms and forecast the next term. Intervals are "
    "split-conformal on relative backtest residuals."
)
SYNTHETIC_NOTE = (
    "Enrollment history is SYNTHETIC (seeded generator, not registrar data). "
    "The backtest validates the forecasting pipeline, not real-world accuracy."
)


# --------------------------------------------------------------------------
# Response schemas
# --------------------------------------------------------------------------
class HistoryPoint(BaseModel):
    semester_id: int
    semester_name: str
    enrolled: int
    waitlist: int


class ModelMetrics(BaseModel):
    mae: float
    smape_pct: float
    last_origin_mae: float
    last_origin_smape_pct: float


class CourseForecast(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    department: str
    history: List[HistoryPoint]
    forecasts: Dict[str, float]
    forecast: float
    interval_80: Tuple[float, float]
    interval_95: Tuple[float, float]


class ForecastMeta(BaseModel):
    target_semester_id: int
    target_semester_name: str
    observed_semester_ids: List[int]
    backtest_origins: List[int]
    champion_model: str
    interval_calibration_n: int
    held_out_coverage_80: Optional[float]
    data_source: str
    is_synthetic: bool
    methodology: str
    note: Optional[str]


class EnrollmentForecastResponse(BaseModel):
    meta: ForecastMeta
    model_metrics: Dict[str, ModelMetrics]
    courses: List[CourseForecast]
    skipped_course_ids: List[int]


class Remedy(BaseModel):
    action: str
    detail: str
    solver_confirmed: bool = False


class BottleneckItem(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    department: str
    requires_lab: bool
    expected_enrollment: int
    forecast: float
    forecast_hi95: float
    max_room_capacity: int
    largest_compatible_room: str
    headroom_pct: float
    capacity_cliff_pct: float
    overflow_probability: float
    rooms_that_fit: int
    risk_tier: str
    remedy: Optional[Remedy]


class SeatBandPressure(BaseModel):
    min_seats: int
    courses_needing: int
    rooms_available: int


class BottleneckSummary(BaseModel):
    tier_counts: Dict[str, int]
    tightest_cliffs: List[BottleneckItem]
    seat_band_pressure: List[SeatBandPressure]


class BottleneckReportResponse(BaseModel):
    meta: ForecastMeta
    summary: BottleneckSummary
    items: List[BottleneckItem]


# --------------------------------------------------------------------------
# Panel construction
# --------------------------------------------------------------------------
@dataclass
class Panel:
    courses: List[Course]
    sem_ids: List[int]          # observed semester ids, ascending
    sem_names: Dict[int, str]
    target_sem_id: int
    Y: np.ndarray               # (n_courses, n_obs) enrolled
    W: np.ndarray               # (n_courses, n_obs) waitlist
    fall: np.ndarray            # (n_obs + 1,) True where the term is a Fall term
    dept_onehot: np.ndarray     # (n_courses, n_depts)
    level: np.ndarray           # (n_courses,) course level (hundreds digit)
    skipped: List[int]
    sources: List[str]


def _course_level(course_code: str) -> float:
    m = re.search(r"\d+", course_code or "")
    if not m:
        return 1.0
    number = int(m.group())
    return float(number // 1000 if number >= 1000 else number // 100) or 1.0


def build_panel(session: Session, target_semester_id: Optional[int] = None) -> Panel:
    obs = session.exec(select(EnrollmentObservation)).all()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enrollment history loaded. Seed the database first.",
        )
    semesters = {s.id: s for s in session.exec(select(Semester)).all()}
    sem_ids = sorted(
        {o.semester_id for o in obs},
        key=lambda sid: (semesters[sid].start_date if sid in semesters else "", sid),
    )
    if len(sem_ids) < MIN_OBSERVED_SEMESTERS:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {MIN_OBSERVED_SEMESTERS} observed semesters.",
        )
    last_sem = semesters.get(sem_ids[-1])
    last_start_date = last_sem.start_date if last_sem is not None else ""
    observed_set = set(sem_ids)
    future_semesters = sorted(
        (
            s
            for s in semesters.values()
            if s.id is not None
            and s.id not in observed_set
            and s.start_date > last_start_date
        ),
        key=lambda s: (s.start_date, s.id),
    )
    target = future_semesters[0].id if future_semesters else sem_ids[-1] + 1
    if target_semester_id is not None and target_semester_id != target:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Only the next unobserved semester ({target}) can be forecast; "
                f"semesters {sem_ids[0]}-{sem_ids[-1]} are already observed."
            ),
        )
    if target not in semesters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semester {target} does not exist.",
        )

    by_course: Dict[int, Dict[int, EnrollmentObservation]] = {}
    for o in obs:
        by_course.setdefault(o.course_id, {})[o.semester_id] = o
    courses = {c.id: c for c in session.exec(select(Course)).all()}

    kept: List[Course] = []
    skipped: List[int] = []
    for cid in sorted(courses):
        series = by_course.get(cid, {})
        if all(s in series for s in sem_ids):
            kept.append(courses[cid])
        elif series:
            skipped.append(cid)
    if not kept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No course has a complete enrollment history.",
        )

    Y = np.array([[by_course[c.id][s].enrolled for s in sem_ids] for c in kept], dtype=float)
    W = np.array([[by_course[c.id][s].waitlist for s in sem_ids] for c in kept], dtype=float)
    Y = np.maximum(Y, 1.0)
    depts = sorted({c.department for c in kept})
    onehot = np.array([[1.0 if c.department == d else 0.0 for d in depts] for c in kept])
    fall = np.array(
        [semesters[s].name.strip().lower().startswith("fall") for s in sem_ids + [target]]
    )
    sources = sorted({o.source for o in obs})
    return Panel(
        courses=kept,
        sem_ids=sem_ids,
        sem_names={s.id: s.name for s in semesters.values()},
        target_sem_id=target,
        Y=Y,
        W=W,
        fall=fall,
        dept_onehot=onehot,
        level=np.array([_course_level(c.course_code) for c in kept]),
        skipped=skipped,
        sources=sources,
    )


# --------------------------------------------------------------------------
# Models: each takes data observed through position T-1 and predicts position T
# --------------------------------------------------------------------------
def _seasonal_naive(p: Panel, T: int) -> np.ndarray:
    return p.Y[:, T - 2].copy()


def _season_gap(logy: np.ndarray, fall: np.ndarray) -> float:
    """Pooled log(Fall / Spring) gap from alternating-season differences."""
    d = logy[:, 1:] - logy[:, :-1]
    fs = fall[:-1] & ~fall[1:]
    sf = ~fall[:-1] & fall[1:]
    if not fs.any() or not sf.any():
        return 0.0
    return float((d[:, sf].mean() - d[:, fs].mean()) / 2.0)


def _holt(z: np.ndarray, alpha: float, beta: float, phi: float):
    level = z[:, 0].copy()
    trend = z[:, 1] - z[:, 0]
    errs = []
    for j in range(1, z.shape[1]):
        pred = level + phi * trend
        errs.append(np.abs(z[:, j] - pred))
        new_level = alpha * z[:, j] + (1 - alpha) * pred
        trend = beta * (new_level - level) + (1 - beta) * phi * trend
        level = new_level
    return level, trend, float(np.mean(errs))


def _damped_trend(p: Panel, T: int) -> np.ndarray:
    logy = np.log(p.Y[:, :T])
    gap = _season_gap(logy, p.fall[:T])
    adj = np.where(p.fall[:T], gap / 2.0, -gap / 2.0)
    z = logy - adj
    best = None
    for alpha in (0.3, 0.5, 0.7):
        for beta in (0.1, 0.3):
            for phi in (0.8, 0.9, 0.98):
                level, trend, err = _holt(z, alpha, beta, phi)
                if best is None or err < best[0]:
                    best = (err, level, trend, phi)
    _, level, trend, phi = best
    season_t = gap / 2.0 if p.fall[T] else -gap / 2.0
    return np.exp(level + phi * trend + season_t)


def _ridge_features(p: Panel, j: int) -> np.ndarray:
    """Features for predicting position j from positions j-1 and j-2."""
    logy1 = np.log(p.Y[:, j - 1])
    logy2 = np.log(p.Y[:, j - 2])
    momentum = logy1 - logy2
    wl = p.W[:, j - 1] / p.Y[:, j - 1]
    fall_j = np.full(p.Y.shape[0], 1.0 if p.fall[j] else 0.0)
    cols = [fall_j, momentum, wl, p.level / 5.0]
    return np.column_stack(cols + [p.dept_onehot])


def _pooled_ridge(p: Panel, T: int) -> np.ndarray:
    X = np.vstack([_ridge_features(p, j) for j in range(2, T)])
    target = np.concatenate(
        [np.log(p.Y[:, j]) - np.log(p.Y[:, j - 1]) for j in range(2, T)]
    )
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < 1e-9] = 1.0
    Xs = (X - mu) / sd
    ybar = target.mean()
    A = Xs.T @ Xs + RIDGE_LAMBDA * np.eye(Xs.shape[1])
    beta = np.linalg.solve(A, Xs.T @ (target - ybar))
    x_new = (_ridge_features(p, T) - mu) / sd
    return np.exp(np.log(p.Y[:, T - 1]) + x_new @ beta + ybar)


MODEL_FUNCS = {
    "seasonal_naive": _seasonal_naive,
    "damped_trend": _damped_trend,
    "pooled_ridge": _pooled_ridge,
}


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
def _mae(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.mean(np.abs(y - yhat)))


def _smape(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.mean(2 * np.abs(y - yhat) / (np.abs(y) + np.abs(yhat))) * 100.0)


@dataclass
class Pipeline:
    panel: Panel
    origins: List[int]
    metrics: Dict[str, ModelMetrics]
    champion: str
    rel_residuals: np.ndarray       # signed relative residuals (y - yhat) / yhat
    held_out_coverage_80: Optional[float]
    forecasts: Dict[str, np.ndarray]


def _conformal_q(abs_rel: np.ndarray, alpha: float) -> float:
    n = len(abs_rel)
    k = min(n, math.ceil((n + 1) * (1 - alpha)))
    return float(np.sort(abs_rel)[k - 1])


def run_pipeline(session: Session, target_semester_id: Optional[int] = None) -> Pipeline:
    p = build_panel(session, target_semester_id)
    n_obs = p.Y.shape[1]
    origins = (
        list(range(4, n_obs))
        if n_obs > 6
        else list(range(max(3, n_obs - 2), n_obs))
    )

    preds: Dict[str, Dict[int, np.ndarray]] = {m: {} for m in MODEL_NAMES}
    for T in origins:
        for name, fn in MODEL_FUNCS.items():
            preds[name][T] = fn(p, T)

    metrics: Dict[str, ModelMetrics] = {}
    for name in MODEL_NAMES:
        y_all = np.concatenate([p.Y[:, T] for T in origins])
        yh_all = np.concatenate([preds[name][T] for T in origins])
        last = origins[-1]
        metrics[name] = ModelMetrics(
            mae=round(_mae(y_all, yh_all), 3),
            smape_pct=round(_smape(y_all, yh_all), 3),
            last_origin_mae=round(_mae(p.Y[:, last], preds[name][last]), 3),
            last_origin_smape_pct=round(_smape(p.Y[:, last], preds[name][last]), 3),
        )
    champion = min(MODEL_NAMES, key=lambda m: metrics[m].mae)

    rel_by_origin = {
        T: (p.Y[:, T] - preds[champion][T]) / preds[champion][T] for T in origins
    }
    rel_all = np.concatenate([rel_by_origin[T] for T in origins])

    coverage = None
    if len(origins) >= 2:
        cal = np.abs(np.concatenate([rel_by_origin[T] for T in origins[:-1]]))
        q = _conformal_q(cal, 0.2)
        coverage = round(float(np.mean(np.abs(rel_by_origin[origins[-1]]) <= q)), 3)

    forecasts = {name: fn(p, n_obs) for name, fn in MODEL_FUNCS.items()}
    return Pipeline(
        panel=p,
        origins=origins,
        metrics=metrics,
        champion=champion,
        rel_residuals=rel_all,
        held_out_coverage_80=coverage,
        forecasts=forecasts,
    )


def _meta(pl: Pipeline) -> ForecastMeta:
    p = pl.panel
    synthetic = "synthetic" in p.sources
    return ForecastMeta(
        target_semester_id=p.target_sem_id,
        target_semester_name=p.sem_names.get(p.target_sem_id, str(p.target_sem_id)),
        observed_semester_ids=p.sem_ids,
        backtest_origins=[p.sem_ids[T] for T in pl.origins],
        champion_model=pl.champion,
        interval_calibration_n=int(len(pl.rel_residuals)),
        held_out_coverage_80=pl.held_out_coverage_80,
        data_source=",".join(p.sources),
        is_synthetic=synthetic,
        methodology=METHODOLOGY,
        note=SYNTHETIC_NOTE if synthetic else None,
    )


def _interval(yhat: float, q: float) -> Tuple[float, float]:
    return round(max(0.0, yhat * (1 - q)), 1), round(yhat * (1 + q), 1)


def get_enrollment_forecast(
    session: Session, semester_id: Optional[int] = None
) -> EnrollmentForecastResponse:
    pl = run_pipeline(session, semester_id)
    p = pl.panel
    abs_rel = np.abs(pl.rel_residuals)
    q80 = _conformal_q(abs_rel, 0.2)
    q95 = _conformal_q(abs_rel, 0.05)
    champ = pl.forecasts[pl.champion]

    items: List[CourseForecast] = []
    for i, c in enumerate(p.courses):
        history = [
            HistoryPoint(
                semester_id=s,
                semester_name=p.sem_names.get(s, str(s)),
                enrolled=int(p.Y[i, k]),
                waitlist=int(p.W[i, k]),
            )
            for k, s in enumerate(p.sem_ids)
        ]
        items.append(
            CourseForecast(
                course_id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                department=c.department,
                history=history,
                forecasts={m: round(float(pl.forecasts[m][i]), 1) for m in MODEL_NAMES},
                forecast=round(float(champ[i]), 1),
                interval_80=_interval(float(champ[i]), q80),
                interval_95=_interval(float(champ[i]), q95),
            )
        )
    return EnrollmentForecastResponse(
        meta=_meta(pl),
        model_metrics=pl.metrics,
        courses=items,
        skipped_course_ids=p.skipped,
    )


# --------------------------------------------------------------------------
# Bottlenecks
# --------------------------------------------------------------------------
def _risk_tier(forecast: float, max_cap: int, headroom_pct: float, p_over: float) -> str:
    if forecast >= max_cap or p_over >= 0.5:
        return "critical"
    if p_over >= 0.2 or headroom_pct < 10:
        return "high"
    if p_over >= 0.05 or headroom_pct < 20:
        return "watch"
    return "ok"


def _remedy(tier: str, forecast: float, hi95: float, max_cap: int, room: str) -> Optional[Remedy]:
    if tier == "ok":
        return None
    if hi95 > max_cap:
        each = math.ceil(forecast / 2)
        return Remedy(
            action="split_section",
            detail=(
                f"Upper forecast {hi95:.0f} exceeds the largest compatible room "
                f"({room}, {max_cap} seats). Split into 2 sections of about {each} seats."
            ),
        )
    return Remedy(
        action="reserve_large_room",
        detail=(
            f"Reserve {room} ({max_cap} seats) early and cap enrollment near "
            f"{int(max_cap * 0.95)} to keep a safety margin."
        ),
    )


def get_bottlenecks(
    session: Session, semester_id: Optional[int] = None
) -> BottleneckReportResponse:
    pl = run_pipeline(session, semester_id)
    p = pl.panel
    rooms = session.exec(select(Room)).all()
    if not rooms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No rooms are configured."
        )
    abs_rel = np.abs(pl.rel_residuals)
    q95 = _conformal_q(abs_rel, 0.05)
    champ = pl.forecasts[pl.champion]
    n_res = len(pl.rel_residuals)

    items: List[BottleneckItem] = []
    for i, c in enumerate(p.courses):
        pool = [r for r in rooms if (not c.requires_lab or r.room_type == "lab")]
        if not pool:
            pool = rooms
        best = max(pool, key=lambda r: r.capacity)
        yhat = float(champ[i])
        hi95 = yhat * (1 + q95)
        headroom = (best.capacity / yhat - 1.0) * 100.0
        threshold = best.capacity / yhat - 1.0
        exceed = int(np.sum(pl.rel_residuals > threshold))
        p_over = (1 + exceed) / (n_res + 1)
        tier = _risk_tier(yhat, best.capacity, headroom, p_over)
        items.append(
            BottleneckItem(
                course_id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                department=c.department,
                requires_lab=c.requires_lab,
                expected_enrollment=c.expected_enrollment,
                forecast=round(yhat, 1),
                forecast_hi95=round(hi95, 1),
                max_room_capacity=best.capacity,
                largest_compatible_room=best.room_number,
                headroom_pct=round(headroom, 1),
                capacity_cliff_pct=round(
                    (best.capacity / max(c.expected_enrollment, 1) - 1.0) * 100.0, 1
                ),
                overflow_probability=round(p_over, 3),
                rooms_that_fit=sum(1 for r in pool if r.capacity >= hi95),
                risk_tier=tier,
                remedy=_remedy(tier, yhat, hi95, best.capacity, best.room_number),
            )
        )

    items.sort(key=lambda x: (RISK_ORDER[x.risk_tier], -x.overflow_probability, x.capacity_cliff_pct))
    tiers = {t: 0 for t in RISK_ORDER}
    for it in items:
        tiers[it.risk_tier] += 1
    cliffs = sorted(items, key=lambda x: (x.capacity_cliff_pct, x.course_code))[:5]
    bands = [
        SeatBandPressure(
            min_seats=s,
            courses_needing=sum(1 for it in items if it.forecast >= s),
            rooms_available=sum(1 for r in rooms if r.capacity >= s),
        )
        for s in LARGE_HALL_THRESHOLDS
    ]
    return BottleneckReportResponse(
        meta=_meta(pl),
        summary=BottleneckSummary(
            tier_counts=tiers, tightest_cliffs=cliffs, seat_band_pressure=bands
        ),
        items=items,
    )
