from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import SessionPrincipal, require_auth
from app.models.entities import User
from app.services.scenario_service import (
    ScenarioResponse,
    ScenarioSpec,
    enforce_instructor_scope,
    redact_for_instructor,
    simulate_scenario,
)

router = APIRouter()

PRIVILEGED_ROLES = ("coordinator", "admin")


def _faculty_name(session: Session, principal: SessionPrincipal) -> str:
    linked = principal.credential.linked_user_id
    user = session.get(User, linked) if linked is not None else None
    if user is None:
        raise HTTPException(
            status_code=403, detail="This account is not linked to a faculty record."
        )
    return user.full_name


@router.post("/simulate", response_model=ScenarioResponse)
def simulate(
    spec: ScenarioSpec,
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Dry-run what-if: nothing is persisted. Faculty may only simulate their own buyout."""
    if principal is None or principal.role in PRIVILEGED_ROLES:
        return simulate_scenario(session, spec)
    own_name = _faculty_name(session, principal)
    enforce_instructor_scope(spec, own_name)
    return redact_for_instructor(simulate_scenario(session, spec), own_name)
