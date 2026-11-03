from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from app.core.security import SessionPrincipal, require_auth
from app.services import copilot_service
from app.services.idf_service import (
    MAX_PDF_BYTES,
    DraftError,
    DraftResponse,
    PRIVACY_NOTE,
    draft_idf,
    extract_pdf_text,
    normalize_text,
    _catalogue,
)
from app.services.clarify_service import ClarifyResponse, build_questions
from app.services.coi_checklist_service import (
    ChecklistRequest,
    ChecklistResponse,
    build_checklist,
)
from app.services.export_service import ExportRequest, build_export
from app.services.lookup_adapters import LookupRequest, LookupResponse, run_lookup
from app.services.matcher_service import MatchRequest, MatchResponse, match_industries
from app.services.policy_service import PolicyAnswer, PolicyQuestion, answer_question

router = APIRouter()


class CommercializationStatus(BaseModel):
    llm_enabled: bool
    model: Optional[str]
    privacy_note: str
    idf_fields: int
    policy_note: str


class TextDraftRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)
    use_llm: bool = False


@router.get("/status", response_model=CommercializationStatus)
def commercialization_status(_p: Optional[SessionPrincipal] = Depends(require_auth)):
    llm = copilot_service.status()
    return CommercializationStatus(
        llm_enabled=llm.llm_enabled,
        model=llm.model,
        privacy_note=PRIVACY_NOTE,
        idf_fields=len(_catalogue()["fields"]),
        policy_note="Answers quote public University of Missouri and UMKC policies. Not legal advice.",
    )


@router.post("/policy/ask", response_model=PolicyAnswer)
def policy_ask(req: PolicyQuestion, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Quote the policy passages that match a question. Nothing is generated or saved."""
    return answer_question(req.question)


@router.post("/idf/draft", response_model=DraftResponse)
async def idf_draft(
    file: UploadFile = File(...),
    use_llm: bool = Form(False),
    _p: Optional[SessionPrincipal] = Depends(require_auth),
):
    """Draft an Invention Disclosure Form from an uploaded PDF. The file is not stored."""
    data = await file.read(MAX_PDF_BYTES + 1)
    try:
        text, pages = extract_pdf_text(data)
        return draft_idf(text, pages_read=pages, use_llm=use_llm)
    except DraftError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/idf/draft-text", response_model=DraftResponse)
def idf_draft_text(req: TextDraftRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Same as /idf/draft for pasted text."""
    try:
        return draft_idf(normalize_text(req.text), use_llm=req.use_llm)
    except DraftError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/match", response_model=MatchResponse)
def match(req: MatchRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Map a technology description to industries, NAICS codes and SBIR/STTR agencies."""
    return match_industries(req.text)


@router.post("/clarify", response_model=ClarifyResponse)
def clarify(draft: DraftResponse, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """A few targeted questions the draft cannot answer. Nothing is stored."""
    return build_questions(draft)


@router.post("/checklist", response_model=ChecklistResponse)
def checklist(req: ChecklistRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Cited compliance to-dos from the author's answers. Nothing is stored."""
    return build_checklist(req)


@router.post("/lookup", response_model=LookupResponse)
def lookup(req: LookupRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """Related papers and federal awards for up to 5 broad terms. Saved results unless live mode is on."""
    return run_lookup(req)


@router.post("/export")
def export_package(req: ExportRequest, _p: Optional[SessionPrincipal] = Depends(require_auth)):
    """A zip of the draft, checklist and market notes, built in memory. Nothing is stored."""
    return Response(
        content=build_export(req),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="commercialization_package.zip"'},
    )
