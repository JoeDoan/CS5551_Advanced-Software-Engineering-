"""Prior-art literature and federal-grant lookups behind one gate.

Default mode serves cached fixtures (real responses saved by data/scripts/build_lookup_fixtures.py).
Live mode (COMMERCIALIZATION_LIVE=true) queries OpenAlex (papers) and NIH RePORTER (awards) with
only the broad terms the author approved, and falls back to fixtures on any failure.
No patent search exists here: no verified patent API was found, so none is claimed.
These results show related work. They are never a novelty or patentability finding.
"""

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import List, Literal, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data" / "commercialization" / "fixtures" / "lookups.json"
OPENALEX_URL = "https://api.openalex.org/works"
NIH_URL = "https://api.reporter.nih.gov/v2/projects/search"
TIMEOUT_S = 8.0
MAX_TERMS = 5
MAX_WORDS = 3
MAX_TERM_CHARS = 30
PER_SOURCE = 5
_TERM_RE = re.compile(r"^[a-z0-9][a-z0-9 \-]*$")

NOTE = (
    "Related published work and federal awards for the broad terms above. This is not a novelty or "
    "patentability finding, and no patent search is included."
)


class LookupItem(BaseModel):
    kind: Literal["literature", "award"]
    title: str
    year: Optional[int] = None
    source: str
    url: str = ""
    detail: str = ""


class LookupRequest(BaseModel):
    terms: List[str] = Field(..., min_length=1, max_length=MAX_TERMS)

    @field_validator("terms")
    @classmethod
    def _broad_terms_only(cls, terms: List[str]) -> List[str]:
        clean = []
        for raw in terms:
            t = " ".join(raw.lower().split())
            if not t or len(t) > MAX_TERM_CHARS or len(t.split()) > MAX_WORDS or not _TERM_RE.match(t):
                raise ValueError(
                    f"Each term must be a short phrase of up to {MAX_WORDS} words ({MAX_TERM_CHARS} characters), "
                    "letters and numbers only."
                )
            if t not in clean:
                clean.append(t)
        return clean


class LookupResponse(BaseModel):
    mode: Literal["fixture", "live"]
    terms: List[str]
    retrieved: str
    items: List[LookupItem]
    message: str
    note: str = NOTE


def live_enabled() -> bool:
    return os.getenv("COMMERCIALIZATION_LIVE", "false").lower() in ("1", "true", "yes")


def fetch_literature(term: str, client: httpx.Client) -> List[LookupItem]:
    res = client.get(OPENALEX_URL, params={
        "filter": f"title_and_abstract.search:{term}",
        "per-page": PER_SOURCE,
        "select": "id,title,publication_year,doi,cited_by_count",
    })
    res.raise_for_status()
    return [
        LookupItem(
            kind="literature", title=w["title"], year=w.get("publication_year"), source="OpenAlex",
            url=w.get("doi") or w["id"], detail=f"Cited {w.get('cited_by_count', 0)} times",
        )
        for w in res.json().get("results", []) if w.get("title")
    ]


def fetch_awards(term: str, client: httpx.Client) -> List[LookupItem]:
    res = client.post(NIH_URL, json={
        "criteria": {"advanced_text_search": {
            "operator": "and", "search_field": "projecttitle,terms", "search_text": term}},
        "limit": PER_SOURCE,
        "include_fields": ["ProjectTitle", "ProjectNum", "FiscalYear", "Organization", "AwardAmount",
                           "ProjectDetailUrl"],
    })
    res.raise_for_status()
    out = []
    for p in res.json().get("results", []):
        if not p.get("project_title"):
            continue
        org = (p.get("organization") or {}).get("org_name", "")
        amount = p.get("award_amount")
        out.append(LookupItem(
            kind="award", title=p["project_title"], year=p.get("fiscal_year"), source="NIH RePORTER",
            url=p.get("project_detail_url", ""),
            detail=", ".join(x for x in (org, f"${amount:,}" if amount else "") if x),
        ))
    return out


def _load_fixtures() -> dict:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _from_fixtures(terms: List[str]) -> LookupResponse:
    data = _load_fixtures()
    items: List[LookupItem] = []
    seen = set()
    for topic, entries in data["topics"].items():
        if any(topic in t or t in topic for t in terms):
            for e in entries:
                if e["title"] not in seen:
                    seen.add(e["title"])
                    items.append(LookupItem(**e))
    msg = (
        f"Saved results from {data['retrieved']} for {len(items)} related items."
        if items else
        f"No saved results for these terms (fixtures saved {data['retrieved']}). Turn on live mode to search."
    )
    return LookupResponse(mode="fixture", terms=terms, retrieved=data["retrieved"], items=items, message=msg)


def run_lookup(req: LookupRequest) -> LookupResponse:
    if not live_enabled():
        return _from_fixtures(req.terms)
    items: List[LookupItem] = []
    seen = set()
    try:
        with httpx.Client(timeout=TIMEOUT_S, headers={"User-Agent": "OptiSched-hackathon (academic demo)"}) as c:
            for term in req.terms:
                for item in fetch_literature(term, c) + fetch_awards(term, c):
                    if item.title not in seen:
                        seen.add(item.title)
                        items.append(item)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        fallback = _from_fixtures(req.terms)
        fallback.message = f"Live search failed ({type(e).__name__}), showing saved results. " + fallback.message
        return fallback
    today = date.today().isoformat()
    return LookupResponse(
        mode="live", terms=req.terms, retrieved=today, items=items,
        message=f"Live results retrieved {today} for: {', '.join(req.terms)}.",
    )
