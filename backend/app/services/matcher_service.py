"""Pain-point and industry matcher: a technology description in, industries out.

Deterministic and offline. The text is matched against a curated map
(backend/data/commercialization/industry_map.json) of industries, their NAICS codes,
typical buyer types, pain points to test and the SBIR/STTR agencies that fund that area.
Every suggestion lists the words in the text that triggered it, so a reader can see why.

This is a starting point for customer-discovery interviews, not market research. It does
not name companies or open SBIR topics, because that data is not in the map.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

MAP_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "commercialization" / "industry_map.json"
)
MAX_TEXT_CHARS = 20_000
MAX_MATCHES = 3
MIN_SCORE = 2.0


class NaicsCode(BaseModel):
    code: str
    title: str


class IndustryMatch(BaseModel):
    id: str
    name: str
    score: float
    matched_terms: List[str]
    naics: List[NaicsCode]
    pain_points: List[str]
    buyer_types: List[str]
    sbir_agencies: List[str]


class MatchRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=MAX_TEXT_CHARS)


class MatchResponse(BaseModel):
    matched: bool
    matches: List[IndustryMatch]
    message: str
    note: str
    naics_source: str
    sbir_topics_url: str


@lru_cache(maxsize=1)
def _map() -> dict:
    with open(MAP_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


@lru_cache(maxsize=None)
def _pattern(keyword: str) -> "re.Pattern[str]":
    """Whole word(s), tolerating common endings: crack -> cracks, cracking; sensor -> sensors."""
    words = [re.escape(w) for w in _norm(keyword).split()]
    return re.compile(r"(?<= )" + " ".join(words) + r"(?:s|es|ed|ing|al)?(?= )")


def match_industries(text: str) -> MatchResponse:
    data = _map()
    haystack = _norm(text)
    scored = []
    for ind in data["industries"]:
        hits = []
        score = 0.0
        for kw in ind["keywords"]:
            count = len(_pattern(kw).findall(haystack))
            if count:
                hits.append(kw)
                score += 1.0 + 0.25 * min(count - 1, 4)
        if score >= MIN_SCORE and len(hits) >= 2:
            scored.append((score, ind, hits))
    scored.sort(key=lambda row: row[0], reverse=True)

    matches = [
        IndustryMatch(
            id=ind["id"], name=ind["name"], score=round(score, 2), matched_terms=hits,
            naics=[NaicsCode(**n) for n in ind["naics"]],
            pain_points=ind["pain_points"], buyer_types=ind["buyer_types"],
            sbir_agencies=ind["sbir_agencies"],
        )
        for score, ind, hits in scored[:MAX_MATCHES]
    ]
    message = (
        "These are starting points. Test each pain point in interviews before relying on it."
        if matches
        else "No industry in the curated map matches this description well enough. "
        "Describe what the technology measures, makes or predicts, in plain words."
    )
    return MatchResponse(
        matched=bool(matches), matches=matches, message=message, note=data["note"],
        naics_source=data["naics_source"], sbir_topics_url=data["sbir_topics_url"],
    )
