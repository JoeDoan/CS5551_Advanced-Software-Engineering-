"""Last gate before an advisor answer leaves the server.

Two rules, both deterministic:
1. Every block names its source. A block without one is dropped.
2. Nothing we wrote may pass a verdict on the user's own work: patentable, novel, "you
   should file", "you are an inventor". Verbatim policy quotes are exempt, because they are
   the policy's words, not ours.
"""

import re
from typing import List, NamedTuple

from app.services.advisor_models import Block

# Verdicts about the person's own invention or choices. General explanations such as
# "an invention is novel if it is not already public" must not trip these, so each pattern
# is tied to "your / this / the invention" or to "you".
_SUBJECT = r"(?:your|this|that|my|our)\s+(?:\w+\s+){0,2}(?:invention|work|idea|technology|discovery|disclosure|method|device|software|result)"
_VERDICT_WORDS = r"(?:patentable|novel|inventive|obvious|an invention|worth patenting|valuable|commercially viable)"
BANNED_PATTERNS = [
    re.compile(rf"\b{_SUBJECT}\b.{{0,30}}\b(?:is|are|isn't|is not|appears to be|seems)\b.{{0,15}}\b{_VERDICT_WORDS}", re.I),
    re.compile(r"\byou(?:'re|\s+are|\s+aren't)(?:\s+not)?\s+(?:an?\s+|the\s+)?(?:co-?)?inventor\b", re.I),
    re.compile(r"\byou\s+should(?:\s+not|n't)?\s+(?:file|patent|publish|sign|disclose|license)\b", re.I),
    re.compile(r"\b(?:it|this|your \w+)\s+(?:will|won't|will not)\s+be\s+(?:granted|approved|patented|accepted)\b", re.I),
    re.compile(r"\b(?:definitely|certainly|clearly)\s+(?:patentable|novel|an invention)\b", re.I),
]


class VerifyResult(NamedTuple):
    blocks: List[Block]
    dropped: List[str]


def claims_filter(text: str) -> List[str]:
    """Return the verdict phrases found in text (empty means clean)."""
    return [m.group(0) for p in BANNED_PATTERNS if (m := p.search(text or ""))]


def verify(blocks: List[Block]) -> VerifyResult:
    kept: List[Block] = []
    dropped: List[str] = []
    for b in blocks:
        if not b.source_label.strip():
            dropped.append(f"{b.type}: no source label")
            continue
        if b.type == "policy_quote":
            if not b.citations:
                dropped.append("policy_quote: no citations")
                continue
            kept.append(b)
            continue
        found = claims_filter(" ".join([b.title, b.body, *b.next_questions]))
        if found:
            dropped.append(f"{b.type}: verdict phrase {found[0]!r}")
            continue
        kept.append(b)
    return VerifyResult(kept, dropped)
