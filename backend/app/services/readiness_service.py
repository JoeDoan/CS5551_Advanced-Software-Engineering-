import re
from typing import List, Literal, Optional

from pydantic import BaseModel

from app.services.idf_service import DraftResponse
from app.services.matcher_service import match_industries

ReadinessDimensionId = Literal[
    "problem",
    "application",
    "difference",
    "evidence",
    "related_work",
    "timing",
]

ReadinessStatus = Literal["stated", "partly", "not_found"]

READINESS_NOTE = (
    "No score and no verdict. This lists what the disclosure does not yet say."
)

_APPLICATION_CUE_RE = re.compile(
    r"\b("
    r"user|users|operator|operators|technician|technicians|nurse|nurses|"
    r"radiologist|radiologists|clinician|clinicians|manager|managers|"
    r"pathologist|pathologists|trainer|trainers|patient|patients|"
    r"inspector|inspectors|buyer|buyers|customer|customers|practitioner|practitioners|"
    r"surgeon|surgeons|physician|physicians|pharmacist|pharmacists|driver|drivers|"
    r"farmer|farmers|grower|growers|chemical\s+plants"
    r")\b",
    re.I,
)

_EVIDENCE_CUE_RE = re.compile(
    r"\b("
    r"tested|measured|results|prototype|validated|wound\s+trials|"
    r"bench\s+trials|usability\s+study|field\s+trials"
    r")\b",
    re.I,
)

_FOLLOW_UP_QUESTIONS = {
    "problem": "What concrete problem or bottleneck does this work address?",
    "application": "Who is the specific user or operator, and what changes in their workflow?",
    "difference": "How does this differ from current practice or competing methods?",
    "evidence": "What data, simulation, or prototype results exist so far?",
    "related_work": "Which closest papers, patents, or existing tools should the office compare against?",
    "timing": "Are any talks, posters, preprints, or theses planned in the next 3 to 6 months?",
}


class ReadinessDimension(BaseModel):
    id: ReadinessDimensionId
    status: ReadinessStatus
    quote: Optional[str] = None
    follow_up: Optional[str] = None
    needs_author: bool


class ReadinessResult(BaseModel):
    dimensions: List[ReadinessDimension]
    note: str = READINESS_NOTE


def _field_quote(draft: DraftResponse, *field_ids: str) -> Optional[str]:
    by_id = {f.id: f for f in draft.fields}
    for fid in field_ids:
        field = by_id.get(fid)
        if field is None:
            continue
        quote = (field.evidence or field.value or "").strip()
        if quote:
            return quote
    return None


def assess(draft: DraftResponse, extra_text: str = "") -> ReadinessResult:
    problem_quote = _field_quote(draft, "A1_problem")
    general_quote = _field_quote(draft, "A1_general", "A1_novel")
    app_quote = _field_quote(draft, "A1_general", "A1_novel", "A1_problem")
    diff_quote = _field_quote(draft, "A1_different", "D1_competition")
    prior_art_quote = _field_quote(draft, "D1_prior_art")
    timing_quote = _field_quote(draft, "A2_first_public", "A3_disclosures")

    draft_app_text = " ".join(
        q for q in (problem_quote, general_quote, _field_quote(draft, "A1_novel")) if q
    )
    combined_app_text = f"{draft_app_text} {extra_text}".strip()
    has_app_cue = bool(_APPLICATION_CUE_RE.search(combined_app_text))

    matcher_hit = False
    if len(draft_app_text) >= 20:
        matcher_hit = match_industries(draft_app_text).matched

    if has_app_cue:
        app_status: ReadinessStatus = "stated"
    elif app_quote or matcher_hit:
        app_status = "partly"
    else:
        app_status = "not_found"

    draft_evidence_text = " ".join(
        q for q in (general_quote, _field_quote(draft, "A1_novel")) if q
    )
    combined_evidence_text = f"{draft_evidence_text} {extra_text}".strip()
    has_evidence_cue = bool(_EVIDENCE_CUE_RE.search(combined_evidence_text))
    has_draft_evidence_cue = bool(_EVIDENCE_CUE_RE.search(draft_evidence_text))

    has_deadline_flag = any(
        fl.level in ("deadline", "warning") for fl in draft.flags
    )
    if timing_quote:
        timing_status: ReadinessStatus = "stated"
    elif has_deadline_flag:
        timing_status = "partly"
    else:
        timing_status = "not_found"

    dimensions = [
        ReadinessDimension(
            id="problem",
            status="stated" if problem_quote else "not_found",
            quote=problem_quote,
            follow_up=None if problem_quote else _FOLLOW_UP_QUESTIONS["problem"],
            needs_author=not bool(problem_quote),
        ),
        ReadinessDimension(
            id="application",
            status=app_status,
            quote=app_quote,
            follow_up=None if app_status == "stated" else _FOLLOW_UP_QUESTIONS["application"],
            needs_author=app_status != "stated",
        ),
        ReadinessDimension(
            id="difference",
            status="stated" if diff_quote else "not_found",
            quote=diff_quote,
            follow_up=None if diff_quote else _FOLLOW_UP_QUESTIONS["difference"],
            needs_author=not bool(diff_quote),
        ),
        ReadinessDimension(
            id="evidence",
            status="stated" if has_evidence_cue else "not_found",
            quote=general_quote if has_draft_evidence_cue else None,
            follow_up=None if has_evidence_cue else _FOLLOW_UP_QUESTIONS["evidence"],
            needs_author=not has_evidence_cue,
        ),
        ReadinessDimension(
            id="related_work",
            status="partly" if prior_art_quote else "not_found",
            quote=prior_art_quote,
            follow_up=_FOLLOW_UP_QUESTIONS["related_work"],
            needs_author=True,
        ),
        ReadinessDimension(
            id="timing",
            status=timing_status,
            quote=timing_quote,
            follow_up=None if timing_status == "stated" else _FOLLOW_UP_QUESTIONS["timing"],
            needs_author=timing_status != "stated",
        ),
    ]

    return ReadinessResult(dimensions=dimensions, note=READINESS_NOTE)
