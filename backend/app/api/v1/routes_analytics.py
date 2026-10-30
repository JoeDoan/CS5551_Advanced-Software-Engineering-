from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.services.analytics_service import (
    ConflictAuditResponse,
    FairnessReportResponse,
    RoomUtilizationReportResponse,
    audit_schedule_conflicts,
    compute_fairness_metrics,
    compute_room_utilization,
)

router = APIRouter()


@router.get(
    "/fairness",
    response_model=FairnessReportResponse,
    tags=["Analytics"],
)
def get_fairness_analytics(
    semester_id: int = Query(
        default=1, description="Target semester ID (1..6)"
    ),
    session: Session = Depends(get_session),
):
    """Retrieve instructor workload, satisfaction, and Gini fairness indices."""
    return compute_fairness_metrics(session=session, semester_id=semester_id)


@router.get(
    "/utilization",
    response_model=RoomUtilizationReportResponse,
    tags=["Analytics"],
)
def get_room_utilization_analytics(
    semester_id: int = Query(
        default=1, description="Target semester ID (1..6)"
    ),
    session: Session = Depends(get_session),
):
    """Retrieve classroom slot utilization and seat occupancy analytics."""
    return compute_room_utilization(session=session, semester_id=semester_id)


@router.get(
    "/conflicts",
    response_model=ConflictAuditResponse,
    tags=["Analytics"],
)
def get_schedule_conflict_audit(
    semester_id: int = Query(
        default=1, description="Target semester ID (1..6)"
    ),
    session: Session = Depends(get_session),
):
    """Audit scheduled events in a semester for hard and soft constraint violations."""
    return audit_schedule_conflicts(session=session, semester_id=semester_id)
