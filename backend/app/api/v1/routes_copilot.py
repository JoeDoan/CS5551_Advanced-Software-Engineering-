from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.v1.routes_scenarios import PRIVILEGED_ROLES, _faculty_name
from app.core.database import get_session
from app.core.security import SessionPrincipal, require_auth
from app.services.copilot_service import (
    AskRequest,
    AskResponse,
    CopilotStatus,
    ParseRequest,
    ParseResponse,
    explain,
    load_vocabulary,
    parse_prompt,
    status,
)
from app.services.scenario_service import (
    enforce_instructor_scope,
    redact_for_instructor,
    simulate_scenario,
)

router = APIRouter()


def _self_name(session: Session, principal: Optional[SessionPrincipal]) -> Optional[str]:
    """Faculty name for scoping, or None for coordinators / unauthenticated dev mode."""
    if principal is None or principal.role in PRIVILEGED_ROLES:
        return None
    return _faculty_name(session, principal)


@router.get("/status", response_model=CopilotStatus)
def copilot_status(_principal: Optional[SessionPrincipal] = Depends(require_auth)):
    """Whether Claude is configured. Never reveals the key."""
    return status()


@router.post("/parse", response_model=ParseResponse)
def parse(
    req: ParseRequest,
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Turn a sentence into a validated scenario spec. Nothing is simulated or saved."""
    own = _self_name(session, principal)
    resp = parse_prompt(
        req.prompt, load_vocabulary(session), use_llm=req.use_llm, self_name=own
    )
    if own is not None and resp.understood:
        enforce_instructor_scope(resp.spec, own)
    return resp


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Run a confirmed spec (or parse a prompt first), then explain the solver's result."""
    own = _self_name(session, principal)
    parsed = None
    spec = req.spec
    if spec is None:
        if not req.prompt:
            raise HTTPException(status_code=422, detail="Provide a prompt or a spec.")
        parsed = parse_prompt(
            req.prompt, load_vocabulary(session), use_llm=req.use_llm, self_name=own
        )
        if not parsed.understood:
            raise HTTPException(status_code=422, detail=" ".join(parsed.warnings))
        spec = parsed.spec
    if own is not None:
        enforce_instructor_scope(spec, own)
    result = simulate_scenario(session, spec)
    if own is not None:
        result = redact_for_instructor(result, own)
    return AskResponse(parse=parsed, result=result, explanation=explain(result))
