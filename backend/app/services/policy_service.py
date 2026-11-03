"""Safe-sandbox policy guardrail: questions in, verbatim policy passages out.

Deterministic and offline. A question is matched against a corpus of public University
of Missouri / UMKC policy text (backend/data/policies/corpus.json, built by
backend/data/scripts/build_policy_corpus.py). The answer is the policy's own words with
a citation to its source, section and version. No language model writes or paraphrases
policy, and when nothing in the corpus matches well enough the service says so instead
of guessing.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "policies" / "corpus.json"

MAX_QUESTION_CHARS = 600
MAX_RESULTS = 5
MIN_DISTINCT_TERMS = 2  # a lone shared word is not evidence
MIN_SCORE = 4.0

DISCLAIMER = (
    "This shows what the written policy says. It is not legal advice and not a "
    "determination. Confirm with the UMKC Conflict of Interest Office (umkccoi@umkc.edu) "
    "and the Office of Technology Commercialization before acting."
)

_STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from has have how i if in into is it its "
    "may me my of on or our shall should that the their them there these they this to was "
    "we what when where which who will with would you your".split()
)

# Plain-language words a faculty member might use -> the terms the policies use.
_SYNONYMS: Dict[str, List[str]] = {
    "startup": ["outside", "interest", "business", "entity", "equity", "company"],
    "company": ["outside", "business", "entity", "equity"],
    "business": ["outside", "entity", "equity"],
    "equity": ["financial", "interest", "ownership"],
    "stock": ["equity", "financial", "interest"],
    "consulting": ["outside", "consulting", "interest"],
    "side": ["outside"],
    "code": ["copyright", "software", "work"],
    "software": ["copyright", "work", "invention"],
    "app": ["software", "copyright", "work"],
    "invention": ["invention", "disclose", "ownership"],
    "patent": ["invention", "patent", "ownership"],
    "own": ["ownership", "rights", "title"],
    "owns": ["ownership", "rights", "title"],
    "royalty": ["income", "royalties", "share"],
    "royalties": ["income", "royalties", "share"],
    "phd": ["student", "students", "enrolled"],
    "grad": ["student", "students"],
    "graduate": ["student", "students"],
    "student": ["students"],
    "students": ["student"],
    "disclose": ["disclosure", "report"],
    "disclosure": ["disclose", "report"],
    "grant": ["sponsored", "federal", "funding"],
    "nsf": ["federal", "investigator"],
    "nih": ["phs", "federal", "investigator"],
    "conflict": ["conflict", "interest"],
}


class PolicyCitation(BaseModel):
    passage_id: str
    source_title: str
    source_url: str
    version: str
    applies_to: str
    section: str
    locator: str
    text: str
    score: float


class PolicyQuestion(BaseModel):
    question: str = Field(..., min_length=3, max_length=MAX_QUESTION_CHARS)


class PolicyAnswer(BaseModel):
    answered: bool
    question: str
    citations: List[PolicyCitation]
    matched_terms: List[str]
    message: str
    disclaimer: str = DISCLAIMER
    corpus_note: str
    corpus_passages: int


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS]


def _stem(word: str) -> str:
    """Tiny suffix stripper so 'students' matches 'student' and 'disclosing' 'disclos'."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _terms(text: str) -> List[str]:
    return [_stem(w) for w in _tokens(text)]


class _Index:
    """BM25 over the corpus passages."""

    K1, B = 1.5, 0.75

    def __init__(self, data: dict):
        self.note: str = data.get("note", "")
        self.passages: List[dict] = data["passages"]
        self.docs = [Counter(_terms(f"{p['section']} {p['text']}")) for p in self.passages]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) if self.lengths else 1.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query_terms: List[str]):
        wanted = set(query_terms)
        scored = []
        for i, doc in enumerate(self.docs):
            hit = wanted & doc.keys()
            if not hit:
                continue
            score = 0.0
            for t in hit:
                tf = doc[t]
                denom = tf + self.K1 * (1 - self.B + self.B * self.lengths[i] / self.avg_len)
                score += self.idf[t] * tf * (self.K1 + 1) / denom
            scored.append((score, i, hit))
        scored.sort(key=lambda row: row[0], reverse=True)
        return scored


@lru_cache(maxsize=1)
def _index() -> _Index:
    with open(CORPUS_PATH, encoding="utf-8") as fh:
        return _Index(json.load(fh))


def _expand(question: str) -> List[str]:
    base = _terms(question)
    extra: List[str] = []
    for word in _tokens(question):
        extra.extend(_stem(s) for s in _SYNONYMS.get(word, []))
    # synonyms count for matching but must not outvote what the user actually wrote
    return base + [t for t in extra if t not in base]


_DOMAIN = frozenset(
    _stem(w)
    for w in (
        list(_SYNONYMS)
        + [w for ws in _SYNONYMS.values() for w in ws]
        + "licence license licensing commercial commercialize sponsor sponsored sponsorship "
        "copyright trademark outside commitment employee faculty investigator compensation "
        "inventor invented discovery intellectual property title waiver nonassertion "
        "sanction noncompliance training management plan".split()
    )
)


def answer_question(question: str) -> PolicyAnswer:
    idx = _index()
    asked = _terms(question)
    if not any(t in _DOMAIN for t in asked):
        return PolicyAnswer(
            answered=False,
            question=question.strip(),
            citations=[],
            matched_terms=[],
            message=(
                "This does not look like a question about conflicts of interest, outside "
                "activities, inventions or ownership, which are the only topics the loaded "
                "policies cover."
            ),
            corpus_note=idx.note,
            corpus_passages=len(idx.passages),
        )
    query = _expand(question)
    ranked = idx.search(query)

    citations: List[PolicyCitation] = []
    seen_text = set()
    for score, i, hit in ranked:
        passage = idx.passages[i]
        if score < MIN_SCORE or len(hit) < MIN_DISTINCT_TERMS:
            continue
        if passage["text"] in seen_text:
            continue
        seen_text.add(passage["text"])
        citations.append(
            PolicyCitation(
                passage_id=passage["id"],
                source_title=passage["source_title"],
                source_url=passage["source_url"],
                version=passage["version"],
                applies_to=passage["applies_to"],
                section=passage["section"],
                locator=passage["locator"],
                text=passage["text"],
                score=round(score, 2),
            )
        )
        if len(citations) == MAX_RESULTS:
            break

    matched = sorted({t for _s, _i, hit in ranked[:MAX_RESULTS] for t in hit} & set(asked))
    if not citations:
        message = (
            "No passage in the loaded policies answers this. That does not mean it is "
            "allowed or forbidden. Ask the UMKC Conflict of Interest Office or the Office "
            "of Technology Commercialization."
        )
    else:
        message = (
            f"Found {len(citations)} passage(s) that may be relevant. They are quoted "
            "exactly as written, with their source and version. Read them in context."
        )
    return PolicyAnswer(
        answered=bool(citations),
        question=question.strip(),
        citations=citations,
        matched_terms=matched,
        message=message,
        corpus_note=idx.note,
        corpus_passages=len(idx.passages),
    )
