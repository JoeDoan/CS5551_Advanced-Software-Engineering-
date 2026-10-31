from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import (
    SessionPrincipal,
    require_auth,
    require_coordinator,
)
from app.models.entities import Course, EditRequest, Room, Schedule, TimeSlot, User
from app.schemas.api_schemas import (
    EditRequestCreate,
    EditRequestResponse,
    EditRequestReview,
)

router = APIRouter()


@dataclass(frozen=True)
class EditRequestMetadata:
    message: str
    proposed_room_id: Optional[int] = None
    proposed_time_slot_id: Optional[int] = None
    reviewer_notes: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "message": self.message,
                "proposed_room_id": self.proposed_room_id,
                "proposed_time_slot_id": self.proposed_time_slot_id,
                "reviewer_notes": self.reviewer_notes,
            }
        )

    @classmethod
    def from_raw(cls, raw: str) -> "EditRequestMetadata":
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "message" in parsed:
                return cls(
                    message=str(parsed["message"]),
                    proposed_room_id=parsed.get("proposed_room_id"),
                    proposed_time_slot_id=parsed.get("proposed_time_slot_id"),
                    reviewer_notes=parsed.get("reviewer_notes"),
                )
        except (json.JSONDecodeError, TypeError):
            pass
        return cls(message=raw)


def _to_response(er: EditRequest) -> EditRequestResponse:
    meta = EditRequestMetadata.from_raw(er.requested_changes)
    return EditRequestResponse(
        id=er.id,
        schedule_id=er.schedule_id,
        requester_id=er.requester_id,
        requested_changes=meta.message,
        proposed_room_id=meta.proposed_room_id,
        proposed_time_slot_id=meta.proposed_time_slot_id,
        reviewer_notes=meta.reviewer_notes,
        status=er.status,
        created_at=er.created_at,
    )


def _apply_approved_schedule_changes(
    session: Session,
    er: EditRequest,
    meta: EditRequestMetadata,
) -> None:
    if meta.proposed_room_id is None and meta.proposed_time_slot_id is None:
        return

    sched = session.get(Schedule, er.schedule_id)
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {er.schedule_id} not found",
        )

    target_room_id = (
        meta.proposed_room_id if meta.proposed_room_id is not None else sched.room_id
    )
    target_slot_id = (
        meta.proposed_time_slot_id
        if meta.proposed_time_slot_id is not None
        else sched.time_slot_id
    )

    room = session.get(Room, target_room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room {target_room_id} not found",
        )
    slot = session.get(TimeSlot, target_slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time slot {target_slot_id} not found",
        )

    course = session.get(Course, sched.course_id)
    if course:
        if room.capacity < course.expected_enrollment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Room '{room.room_number}' capacity ({room.capacity}) is less "
                    f"than course expected enrollment ({course.expected_enrollment})"
                ),
            )
        if course.requires_lab and room.room_type.lower() != "lab":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Course '{course.course_code}' requires a lab room",
            )

    room_conflict = session.exec(
        select(Schedule).where(
            Schedule.semester_id == sched.semester_id,
            Schedule.room_id == target_room_id,
            Schedule.time_slot_id == target_slot_id,
            Schedule.id != sched.id,
        )
    ).first()
    if room_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot approve: room '{room.room_number}' is already booked "
                f"in time slot {target_slot_id}"
            ),
        )

    inst_conflict = session.exec(
        select(Schedule).where(
            Schedule.semester_id == sched.semester_id,
            Schedule.user_id == sched.user_id,
            Schedule.time_slot_id == target_slot_id,
            Schedule.id != sched.id,
        )
    ).first()
    if inst_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot approve: instructor is already assigned in time slot "
                f"{target_slot_id}"
            ),
        )

    sched.room_id = target_room_id
    sched.time_slot_id = target_slot_id
    sched.status = "revised"
    session.add(sched)


@router.post(
    "",
    response_model=EditRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_edit_request(
    payload: EditRequestCreate,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Submit an instructor schedule change request."""
    sched = session.get(Schedule, payload.schedule_id)
    if not sched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {payload.schedule_id} not found",
        )

    requester = session.get(User, payload.requester_id)
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {payload.requester_id} not found",
        )

    if payload.proposed_room_id is not None:
        if not session.get(Room, payload.proposed_room_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proposed room {payload.proposed_room_id} not found",
            )

    if payload.proposed_time_slot_id is not None:
        if not session.get(TimeSlot, payload.proposed_time_slot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Proposed time slot {payload.proposed_time_slot_id} not found"
                ),
            )

    meta = EditRequestMetadata(
        message=payload.requested_changes,
        proposed_room_id=payload.proposed_room_id,
        proposed_time_slot_id=payload.proposed_time_slot_id,
    )
    er = EditRequest(
        schedule_id=payload.schedule_id,
        requester_id=payload.requester_id,
        requested_changes=meta.to_json(),
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(er)
    session.commit()
    session.refresh(er)
    return _to_response(er)


@router.get("", response_model=List[EditRequestResponse])
def list_edit_requests(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status (pending, approved, rejected)",
    ),
    requester_id: Optional[int] = Query(
        default=None, description="Filter by requester user ID"
    ),
    schedule_id: Optional[int] = Query(
        default=None, description="Filter by schedule ID"
    ),
    session: Session = Depends(get_session),
):
    """List schedule edit requests with optional filtering."""
    stmt = select(EditRequest)
    if status_filter is not None:
        stmt = stmt.where(EditRequest.status == status_filter)
    if requester_id is not None:
        stmt = stmt.where(EditRequest.requester_id == requester_id)
    if schedule_id is not None:
        stmt = stmt.where(EditRequest.schedule_id == schedule_id)
    return [_to_response(r) for r in session.exec(stmt).all()]


@router.get("/{request_id}", response_model=EditRequestResponse)
def get_edit_request(
    request_id: int,
    session: Session = Depends(get_session),
):
    """Retrieve a single edit request by ID."""
    er = session.get(EditRequest, request_id)
    if not er:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edit request {request_id} not found",
        )
    return _to_response(er)


@router.patch("/{request_id}/review", response_model=EditRequestResponse)
def review_edit_request(
    request_id: int,
    payload: EditRequestReview,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Approve or reject a pending edit request and update schedule on approval."""
    er = session.get(EditRequest, request_id)
    if not er:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edit request {request_id} not found",
        )

    if er.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Edit request {request_id} has already been {er.status}",
        )

    meta = EditRequestMetadata.from_raw(er.requested_changes)
    if payload.status == "approved":
        _apply_approved_schedule_changes(session, er, meta)

    updated_meta = EditRequestMetadata(
        message=meta.message,
        proposed_room_id=meta.proposed_room_id,
        proposed_time_slot_id=meta.proposed_time_slot_id,
        reviewer_notes=payload.reviewer_notes,
    )
    er.status = payload.status
    er.requested_changes = updated_meta.to_json()
    session.add(er)
    session.commit()
    session.refresh(er)
    return _to_response(er)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edit_request(
    request_id: int,
    session: Session = Depends(get_session),
    _principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Delete an edit request."""
    er = session.get(EditRequest, request_id)
    if not er:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edit request {request_id} not found",
        )
    session.delete(er)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
