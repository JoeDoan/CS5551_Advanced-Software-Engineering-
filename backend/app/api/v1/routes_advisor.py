from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.security import SessionPrincipal, require_auth
from app.services import advisor_service, glossary_service, readiness_service
from app.services.advisor_models import AdvisorRequest, AdvisorResponse, GlossaryEntry
from app.services.readiness_service import ReadinessRequest, ReadinessResult

router = APIRouter()


@router.post("/advisor/ask", response_model=AdvisorResponse)
def advisor_ask(req: AdvisorRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Sourced blocks for one question. Nothing is stored or logged."""
    return advisor_service.respond(req.question)


@router.post("/readiness", response_model=ReadinessResult)
def readiness(req: ReadinessRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """What the draft does not say yet, across six dimensions. No score, no verdict, nothing stored."""
    return readiness_service.assess(req.draft, req.extra_text, req.covered_elsewhere)


@router.get("/glossary", response_model=List[GlossaryEntry])
def glossary(_p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Plain-language explainers. Each carries its review status."""
    return glossary_service.list_entries()
