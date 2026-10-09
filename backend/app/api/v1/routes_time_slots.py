from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, or_

from app.core.database import get_session
from app.models.entities import TimeSlot
from app.schemas.api_schemas import TimeSlotResponse

router = APIRouter()


@router.get("", response_model=List[TimeSlotResponse])
def list_time_slots(
    day_pattern: Optional[str] = Query(default=None, description="e.g. MWF, TR"),
    level: Optional[str] = Query(default=None, description="undergraduate, graduate"),
    session: Session = Depends(get_session),
):
    """Retrieve catalog time slots with optional day pattern and level filters."""
    stmt = select(TimeSlot)
    if day_pattern:
        stmt = stmt.where(TimeSlot.day_pattern == day_pattern.upper())
    if level:
        stmt = stmt.where(or_(TimeSlot.level == level, TimeSlot.level.is_(None)))
    return session.exec(stmt).all()
