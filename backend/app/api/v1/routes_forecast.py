from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import SessionPrincipal, require_auth
from app.services.foia_replay_service import (
    EmpiricalBenchmarkResponse,
    get_empirical_benchmark,
)
from app.services.forecast_service import (
    BottleneckReportResponse,
    EnrollmentForecastResponse,
    get_bottlenecks,
    get_enrollment_forecast,
)

router = APIRouter()


@router.get("/enrollment", response_model=EnrollmentForecastResponse)
def enrollment_forecast(
    semester_id: Optional[int] = Query(
        default=None,
        description="Target semester; only the next unobserved semester is supported.",
    ),
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Per-course enrollment history, 3-model forecasts, intervals and backtest metrics."""
    return get_enrollment_forecast(session=session, semester_id=semester_id)


@router.get("/bottlenecks", response_model=BottleneckReportResponse)
def bottleneck_report(
    semester_id: Optional[int] = Query(
        default=None,
        description="Target semester; only the next unobserved semester is supported.",
    ),
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Room-capacity risk per course: overflow probability, headroom and capacity cliff."""
    return get_bottlenecks(session=session, semester_id=semester_id)


@router.get("/empirical-benchmark", response_model=EmpiricalBenchmarkResponse)
def empirical_benchmark(
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Non-circular 19-term FOIA forecast & CP-SAT benchmark vs Spring 2026."""
    return get_empirical_benchmark(session=session)
