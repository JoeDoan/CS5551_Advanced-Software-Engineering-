"""Readiness coach: what the disclosure draft does not say yet, in six plain dimensions.

Deterministic and offline. For each dimension it reports whether the author's own draft (or
the optional extra text they typed) states it, quotes the sentence that does, and, where the
dimension is missing or thin, asks one fixed follow-up question. It never scores, ranks or
judges. "Not found" means "this text does not say it", not "it is absent from the work".

Human-only form fields (for example A2_prototype) are always blank in the draft, so evidence
and stage are read from cue words in what the author wrote, not from those fields.
Nothing here is stored or logged.
"""

import re
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from app.services.idf_service import DraftResponse
from app.services.matcher_service import match_industries

DimensionId = Literal["problem", "application", "difference", "evidence", "related_work", "timing"]
Status = Literal["stated", "partly", "not_found"]

DIMENSION_ORDER: List[str] = ["problem", "application", "difference", "evidence", "related_work", "timing"]
MAX_EXTRA_CHARS = 1500
MAX_QUOTE_CHARS = 300

NOTE = "No score and no verdict. This lists what the disclosure does not yet say."

# One fixed question per dimension, asked only when that dimension has a gap.
FOLLOW_UPS: Dict[str, str] = {
    "problem": "What problem does this solve, and who has it today?",
    "application": "Who would use this, and what do they do today instead?",
    "difference": "What is the closest existing alternative, and what exactly does yours do differently?",
    "evidence": "What has been built or tested so far, and under what conditions?",
    "related_work": "Which existing paper, product or method is closest to yours, and how does yours differ?",
    "timing": "Has any of this been shared outside your group, and is a paper, talk or poster coming up?",
}

TITLES: Dict[str, str] = {
    "problem": "Problem",
    "application": "Application or user",
    "difference": "Difference from others",
    "evidence": "Evidence or stage",
    "related_work": "Related work",
    "timing": "Timing",
}

_USER_CUE = re.compile(
    r"\b(?:users?|customers?|clients?|buyers?|consumers?|clinicians?|physicians?|doctors?|patients?|"
    r"inspectors?|operators?|engineers?|farmers?|manufacturers?|hospitals?|utilit(?:y|ies)|"
    r"agenc(?:y|ies)|compan(?:y|ies)|industry|practitioners?|teachers?|drivers?|"
    r"departments? of transportation|used (?:by|in)|for use (?:by|in)|applications? (?:in|for)|"
    r"(?:would|could|will|can)\s+(?:be\s+)?used?)\b",
    re.I,
)
_EVIDENCE_CUES = (
    "tested", "testing", "measured", "measurement", "results", "prototype", "validated",
    "validation", "field trial", "experiment", "demonstrated", "pilot", "benchmark",
)
_TIMING_CUE = re.compile(
    r"\b(?:published|presented|preprint|poster|talk|conference|submitted|submission|"
    r"workshop|proceedings?|defen[cs]e|thesis|website|seminar)\b",
    re.I,
)
_NARRATIVE = ("A1_problem", "A1_general", "A1_novel", "A1_technical", "A1_different", "A1_limits")
_APPLICATION_SOURCES = ("A1_problem", "A1_general", "A1_novel")


class Dimension(BaseModel):
    id: DimensionId
    status: Status
    quote: Optional[str] = None
    follow_up: Optional[str] = None
    needs_author: bool


class ReadinessRequest(BaseModel):
    draft: DraftResponse
    extra_text: str = Field(default="", max_length=MAX_EXTRA_CHARS)
    covered_elsewhere: List[DimensionId] = Field(default_factory=list)


class ReadinessResult(BaseModel):
    dimensions: List[Dimension]
    note: str = NOTE


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _cap(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= MAX_QUOTE_CHARS:
        return text
    cut = text[:MAX_QUOTE_CHARS]
    return cut[: cut.rfind(" ")] if " " in cut else cut  # a prefix, so it is still a true excerpt


def _sentence_with(text: str, pattern: "re.Pattern[str]") -> Optional[str]:
    for s in _SENTENCE_SPLIT.split(" ".join(text.split())):
        if pattern.search(s):
            return _cap(s)
    return None


def _field_text(draft: DraftResponse, field_id: str) -> str:
    f = next((x for x in draft.fields if x.id == field_id), None)
    return (f.evidence or f.value).strip() if f else ""


def _sources(draft: DraftResponse, ids, extra: str) -> List[str]:
    texts = [t for t in (_field_text(draft, i) for i in ids) if t]
    if extra.strip():
        texts.append(" ".join(extra.split()))
    return texts


def _problem(draft, extra) -> Tuple[Status, Optional[str]]:
    text = _field_text(draft, "A1_problem")
    return ("stated", _cap(text)) if text else ("not_found", None)


def _application(draft, extra) -> Tuple[Status, Optional[str]]:
    texts = _sources(draft, _APPLICATION_SOURCES, extra)
    for t in texts:
        quote = _sentence_with(t, _USER_CUE)
        if quote:
            return "stated", quote
    if texts and match_industries(" ".join(texts)).matched:
        return "partly", None  # the matcher found an industry, but nobody said who would use it
    return "not_found", None


def _difference(draft, extra) -> Tuple[Status, Optional[str]]:
    for fid in ("A1_different", "D1_competition"):
        text = _field_text(draft, fid)
        if text:
            return "stated", _cap(text)
    return "not_found", None


def _evidence(draft, extra) -> Tuple[Status, Optional[str]]:
    pattern = re.compile("|".join(re.escape(c) for c in _EVIDENCE_CUES), re.I)
    found, quote = set(), None
    for t in _sources(draft, _NARRATIVE, extra):
        found.update(m.group(0).lower() for m in pattern.finditer(t))
        quote = quote or _sentence_with(t, pattern)
    if len(found) >= 2:  # two different cue words, not one word repeated
        return "stated", quote
    if found:
        return "partly", quote
    return "not_found", None


def _related_work(draft, extra) -> Tuple[Status, Optional[str]]:
    text = _field_text(draft, "D1_prior_art")
    # Present is only "partly": whether it is the right prior art needs the author to check.
    return ("partly", _cap(text)) if text else ("not_found", None)


def _timing(draft, extra) -> Tuple[Status, Optional[str]]:
    for fid in ("A2_first_public", "A3_disclosures"):
        text = _field_text(draft, fid)
        if text:
            return "stated", _cap(text)
    if extra.strip():
        quote = _sentence_with(extra, _TIMING_CUE)
        if quote:
            return "partly", quote
    if any(f.level == "deadline" for f in draft.flags):
        return "partly", None
    return "not_found", None


_RULES = {
    "problem": _problem,
    "application": _application,
    "difference": _difference,
    "evidence": _evidence,
    "related_work": _related_work,
    "timing": _timing,
}


def assess(draft: DraftResponse, extra_text: str = "", covered_elsewhere: Optional[List[str]] = None) -> ReadinessResult:
    """Six dimensions, in a fixed order. The author may mark a dimension as covered elsewhere."""
    covered = set(covered_elsewhere or [])
    extra = (extra_text or "")[:MAX_EXTRA_CHARS]
    dims: List[Dimension] = []
    for dim_id in DIMENSION_ORDER:
        status, quote = _RULES[dim_id](draft, extra)
        gap = status != "stated" and dim_id not in covered
        dims.append(
            Dimension(
                id=dim_id,
                status=status,
                quote=quote,
                follow_up=FOLLOW_UPS[dim_id] if gap else None,
                # Timing dates and related work always need the author to confirm them.
                needs_author=gap or (dim_id in ("timing", "related_work") and status != "not_found"),
            )
        )
    return ReadinessResult(dimensions=dims)
