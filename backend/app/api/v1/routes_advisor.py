from typing import Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import SessionPrincipal, require_auth
from app.services import advisor_service, glossary_service, readiness_service
from app.services.advisor_service import AdvisorResponse
from app.services.glossary_service import GlossaryResult
from app.services.idf_service import (
    PRIVACY_NOTE,
    DraftField,
    DraftFlag,
    DraftResponse,
)
from app.services.policy_service import MAX_QUESTION_CHARS
from app.services.readiness_service import ReadinessResult

router = APIRouter()


class PartialDraftPayload(BaseModel):
    extractor: Literal["rules", "claude"] = "rules"
    llm_status: str = "disabled"
    pages_read: int = 0
    chars_read: int = 0
    fields: List[DraftField] = Field(default_factory=list)
    flags: List[DraftFlag] = Field(default_factory=list)
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"proposed": 0, "needs_author": 0, "blank": 0}
    )
    warnings: List[str] = Field(default_factory=list)
    privacy_note: str = PRIVACY_NOTE
    form_url: str = ""
    returns_to: str = ""

    def to_draft_response(self) -> DraftResponse:
        return DraftResponse(**self.model_dump())


class AdvisorAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=MAX_QUESTION_CHARS)
    draft: Optional[Union[DraftResponse, PartialDraftPayload]] = None


class ReadinessRequest(BaseModel):
    draft: Union[DraftResponse, PartialDraftPayload]
    extra_text: str = Field(default="", max_length=2000)


def _coerce_draft(
    draft: Optional[Union[DraftResponse, PartialDraftPayload]],
) -> Optional[DraftResponse]:
    if draft is None:
        return None
    if isinstance(draft, DraftResponse):
        return draft
    return draft.to_draft_response()


@router.post("/advisor", response_model=AdvisorResponse)
@router.post("/advisor/ask", response_model=AdvisorResponse)
def advisor_ask(
    req: AdvisorAskRequest,
    _p: Optional[SessionPrincipal] = Depends(require_auth),
) -> AdvisorResponse:
    return advisor_service.respond(req.question, draft=_coerce_draft(req.draft))


@router.post("/readiness", response_model=ReadinessResult)
def readiness_assess(
    req: ReadinessRequest,
    _p: Optional[SessionPrincipal] = Depends(require_auth),
) -> ReadinessResult:
    coerced = _coerce_draft(req.draft)
    assert coerced is not None
    return readiness_service.assess(coerced, req.extra_text)


@router.get("/glossary", response_model=GlossaryResult)
def glossary_list(
    _p: Optional[SessionPrincipal] = Depends(require_auth),
) -> GlossaryResult:
    return glossary_service.list_glossary()
