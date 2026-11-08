import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

GLOSSARY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "commercialization" / "glossary.json"
)

DEFAULT_SOURCE_LABEL = "General explainer, draft, not yet reviewed by the technology office"


class GlossaryEntry(BaseModel):
    term: str
    plain: str
    example: str
    what_office_asks: str
    related_fields: List[str]
    reviewed_by: Optional[str] = None
    reviewed_on: Optional[str] = None
    source_label: str = DEFAULT_SOURCE_LABEL


class GlossaryResult(BaseModel):
    entries: List[GlossaryEntry]
    source_label: str = DEFAULT_SOURCE_LABEL


_ALIASES: Dict[str, Tuple[str, ...]] = {
    "novelty": ("novelty",),
    "prior art": ("prior art",),
    "inventorship": ("inventorship",),
    "public disclosure": ("public disclosure", "public disclosures"),
    "development stage": ("development stage",),
    "translational readiness": ("translational readiness",),
    "potential application": ("potential application", "potential applications"),
    "differentiation": ("differentiation",),
    "conflict of interest": ("conflict of interest", "conflicts of interest"),
    "invention disclosure": ("invention disclosure",),
    "licence": ("licence", "license", "licensing"),
    "equity": ("equity",),
}

_DEFINITIONAL_CUE_RE = re.compile(
    r"^(?:"
    r"what\s+(?:is|are)\s+(?:a|an|the)?\s*|"
    r"what\s+does\s+|"
    r"what\s+do\s+you\s+mean\s+by\s+|"
    r"what\s+is\s+meant\s+by\s+|"
    r"what\s+counts\s+as\s+(?:a|an|the)?\s*|"
    r"define\s+|"
    r"definition\s+of\s+|"
    r"meaning\s+of\s+|"
    r"explain\s+|"
    r"how\s+is\s+inventorship\s+different\s+from\s+authorship"
    r")",
    re.I,
)

_NON_DEFINITIONAL_RE = re.compile(
    r"\b(?:"
    r"what\s+happens|"
    r"to\s+whom|"
    r"dollar\s+threshold|"
    r"substantial\s+use|"
    r"conditions\s+for|"
    r"sanctions\s+apply|"
    r"obligations\s+under|"
    r"how\s+often|"
    r"when\s+must|"
    r"who\s+owns|"
    r"who\s+appoints|"
    r"how\s+are\s+net|"
    r"how\s+is\s+net|"
    r"can\s+(?:i|my|we|an|the)|"
    r"do\s+(?:i|we|invention)|"
    r"does\s+(?:the\s+university|section)"
    r")\b",
    re.I,
)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@lru_cache(maxsize=1)
def list_glossary() -> GlossaryResult:
    with open(GLOSSARY_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    source_label = raw.get("source_label", DEFAULT_SOURCE_LABEL)
    entries = [
        GlossaryEntry(
            **{
                **entry,
                "source_label": entry.get("source_label", source_label),
            }
        )
        for entry in raw.get("entries", [])
    ]
    return GlossaryResult(entries=entries, source_label=source_label)


def lookup(question: str) -> Optional[GlossaryEntry]:
    cleaned = _norm(question)
    if not cleaned:
        return None

    glossary = list_glossary()
    by_key = {entry.term.lower(): entry for entry in glossary.entries}

    for key, aliases in _ALIASES.items():
        if cleaned in aliases and key in by_key:
            return by_key[key]

    if _NON_DEFINITIONAL_RE.search(cleaned):
        return None

    if not _DEFINITIONAL_CUE_RE.search(cleaned):
        return None

    padded = f" {cleaned} "
    matches: List[Tuple[int, int, GlossaryEntry]] = []
    for key, aliases in _ALIASES.items():
        entry = by_key.get(key)
        if entry is None:
            continue
        for alias in aliases:
            pos = padded.find(f" {alias} ")
            if pos != -1:
                matches.append((pos, -len(alias), entry))
                break

    if not matches:
        return None

    matches.sort(key=lambda item: (item[0], item[1]))
    return matches[0][2]
