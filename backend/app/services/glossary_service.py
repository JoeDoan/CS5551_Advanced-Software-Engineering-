"""Plain-language explainers for the terms faculty ask about first.

Entries live in backend/data/commercialization/glossary.json. They are written by the
project team, are not University policy, and say so on every block until the technology
office fills in reviewed_by and reviewed_on. Lookup is exact-alias matching, so a definition
question like "What is a conflict of interest?" is answered here instead of being refused by
the policy search, whose score floor is meant for retrieval, not definitions.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from app.services.advisor_models import Block, GlossaryEntry
from app.services.policy_service import answer_question
from app.services.scope_service import MEANING_REQUEST, strip_filler

GLOSSARY_PATH = Path(__file__).resolve().parents[2] / "data" / "commercialization" / "glossary.json"

SOURCE_DRAFT = "General explainer, draft, not yet reviewed by the technology office"
MAX_QUOTES_WITH_ENTRY = 2

_DEFINITION_LEAD = re.compile(
    r"^\s*(?:what(?:'s|\s+is|\s+are|\s+does|\s+do)|define|explain|meaning\s+of|tell\s+me\s+about|describe|"
    r"what\s+is\s+the\s+difference\s+between|difference\s+between)\s+",
    re.I,
)
_FILLER = re.compile(r"\b(?:a|an|the|mean|means|meaning|term|word)\b", re.I)
MAX_BARE_WORDS = 4


def _source_label(raw: dict) -> str:
    if raw.get("reviewed_by") and raw.get("reviewed_on"):
        return f"General explainer, reviewed by {raw['reviewed_by']} on {raw['reviewed_on']}"
    return SOURCE_DRAFT


@lru_cache(maxsize=1)
def _raw_entries() -> List[dict]:
    with open(GLOSSARY_PATH, encoding="utf-8") as fh:
        return json.load(fh)["entries"]


def _entry(raw: dict) -> GlossaryEntry:
    return GlossaryEntry(
        id=raw["id"],
        term=raw["term"],
        aliases=raw["aliases"],
        plain=raw["plain"],
        example=raw["example"],
        think_about=raw["think_about"],
        related_fields=raw["related_fields"],
        related=raw["related"],
        reviewed_by=raw.get("reviewed_by"),
        reviewed_on=raw.get("reviewed_on"),
        source_label=_source_label(raw),
    )


def list_entries() -> List[GlossaryEntry]:
    return [_entry(r) for r in _raw_entries()]


def get(entry_id: str) -> Optional[GlossaryEntry]:
    return next((_entry(r) for r in _raw_entries() if r["id"] == entry_id), None)


def _alias_pattern(alias: str) -> re.Pattern:
    return re.compile(rf"(?<![\w-]){re.escape(alias)}s?(?![\w-])", re.I)


def lookup(question: str, limit: int = 2) -> List[GlossaryEntry]:
    """Entries the question is asking about. Only definitional or bare-term questions match.

    "What is novelty?", "define prior art", "novelty" match. A long question that happens to
    mention a term does not, so it still goes to the policy search.
    """
    q = strip_filler(question).rstrip("?.! ")
    lead = _DEFINITION_LEAD.match(q)
    broad = False  # an explain request somewhere in a longer question ("... What does that mean?")
    if lead:
        phrase = q[lead.end():]
    elif MEANING_REQUEST.search(q):
        phrase, broad = q, True
    else:
        words = re.findall(r"[\w'-]+", q)
        if not words or len(words) > MAX_BARE_WORDS:
            return []
        phrase = q
    cleaned = " ".join(_FILLER.sub(" ", phrase).split())
    if not cleaned:
        return []

    hits = []  # (position, alias length, raw entry)
    for raw in _raw_entries():
        best = None
        for alias in raw["aliases"]:
            # In a long question only a specific name counts, not a common word like "stage" or "stock".
            if broad and " " not in alias and alias.lower() != raw["term"].lower():
                continue
            m =_alias_pattern(alias).search(cleaned) or _alias_pattern(alias).search(phrase)
            if m and (best is None or len(alias) > best[1]):
                best = (m.start(), len(alias))
        if best:
            hits.append((best[0], -best[1], raw))
    if not hits:
        return []
    hits.sort(key=lambda h: (h[0], h[1]))
    chosen, spans = [], []
    for pos, neg_len, raw in hits:  # drop an entry whose match sits inside a longer, earlier one
        if any(pos >= s and pos < s + n for s, n in spans):
            continue
        spans.append((pos, -neg_len))
        chosen.append(raw)
        if len(chosen) == limit:
            break
    return [_entry(r) for r in chosen]


def to_block(entry: GlossaryEntry, with_policy: bool = True) -> List[Block]:
    """The glossary block for an entry, plus up to two quoted policy passages when one is mapped."""
    body = f"{entry.plain}\n\nExample: {entry.example}\n\nThink about: " + " ".join(entry.think_about)
    chips = [f"What is {t.term.lower()}?" for rid in entry.related if (t := get(rid))][:3]
    blocks = [
        Block(type="glossary", source_label=entry.source_label, title=entry.term, body=body, next_questions=chips)
    ]
    raw = next(r for r in _raw_entries() if r["id"] == entry.id)
    query = raw.get("policy_query")
    if with_policy and query:
        ans = answer_question(query)
        if ans.answered:
            cites = ans.citations[: raw.get("policy_max", MAX_QUOTES_WITH_ENTRY)]
            first = cites[0]
            blocks.append(
                Block(
                    type="policy_quote",
                    source_label=f"Quoted policy: {first.source_title}, {first.version}",
                    title=f"What the written policy says about {entry.term.lower()}",
                    body=ans.disclaimer,
                    citations=cites,
                )
            )
    return blocks
