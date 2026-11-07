from typing import List, Optional

from fastapi import APIRouter, Depends

from app.core.security import SessionPrincipal, require_auth
from app.services import advisor_service, glossary_service
from app.services.advisor_models import AdvisorRequest, AdvisorResponse, GlossaryEntry

router = APIRouter()


@router.post("/advisor/ask", response_model=AdvisorResponse)
def advisor_ask(req: AdvisorRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Sourced blocks for one question. Nothing is stored or logged."""
    return advisor_service.respond(req.question)


@router.get("/glossary", response_model=List[GlossaryEntry])
def glossary(_p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Plain-language explainers. Each carries its review status."""
    return glossary_service.list_entries()
