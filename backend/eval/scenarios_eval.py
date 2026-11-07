"""Scenario and readiness evaluation. Offline and deterministic: no network, no model.

The rubric is structural, not a judgement of how well the language reads. Each scenario is
scored 0, 1 or 2 on five dimensions:

  routing     the intent is the one the sponsor brief requires (policy, concept, referral...)
  sourcing    every block names its source; every quoted passage is verbatim from the corpus;
              no block was dropped by the verifier
  boundary    no verdict or legal wording in our own text; no policy quotes where a referral or
              refusal is required; no invented timeline
  usefulness  the expected content is present (a quote from an expected source, the expected
              glossary entries, a referral that names the office and what to bring)
  next_step   the user is told what to do next (follow-up chips or a named office)

A scenario passes at a total of 7 or more out of 10 AND a full score on routing, sourcing and
boundary. The scenarios are synthetic, written by the project team, and 25 is a small sample.
"""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from app.services import glossary_service, idf_service as idf, policy_service
from app.services.advisor_service import respond_audited
from app.services.readiness_service import assess
from app.services.verifier import claims_filter

HERE = Path(__file__).resolve().parent
SCENARIOS_PATH = HERE / "scenarios.json"
DRAFTS_PATH = HERE / "readiness_drafts.json"

DIMENSIONS = ("routing", "sourcing", "boundary", "usefulness", "next_step")
HARD_GATES = ("routing", "sourcing", "boundary")
PASS_AT = 7

_CORPUS = {p["id"]: p for p in json.loads(policy_service.CORPUS_PATH.read_text(encoding="utf-8"))["passages"]}
_TIMELINE = re.compile(r"\b\d+\s*(?:business\s+)?(?:days?|weeks?|months?)\b", re.I)


def sha256_of(path: Path) -> str:
    """Hash with line endings normalised, so a CRLF checkout does not change it."""
    return hashlib.sha256(path.read_bytes().replace(bytes([13, 10]), bytes([10]))).hexdigest()


def _own_text(res) -> str:
    """Text the team wrote (everything except verbatim policy quotes)."""
    return " ".join(f"{b.title} {b.body}" for b in res.blocks if b.type != "policy_quote")


def _usefulness(item: dict, res) -> int:
    expect = item.get("expect_intent_any") or [item["expect_intent"]]
    quotes = [b for b in res.blocks if b.type == "policy_quote"]
    if "policy" in expect:
        cites = [c for b in quotes for c in b.citations]
        phrase = item.get("expect_phrase")
        hit = [
            c for c in cites
            if c.passage_id.split("#")[0] in item["expect_sources"] and (not phrase or phrase.lower() in c.text.lower())
        ]
        return 2 if hit else (1 if quotes else 0)
    if item.get("expect_glossary"):
        titles = {b.title for b in res.blocks if b.type == "glossary"}
        wanted = {glossary_service.get(g).term for g in item["expect_glossary"]}
        return 2 if wanted <= titles else (1 if titles else 0)
    if item.get("expect_title"):
        return 2 if any(b.title == item["expect_title"] for b in res.blocks) else 0
    if "out_of_scope" in expect:
        return 2 if res.blocks and not quotes else 0
    refs = [b for b in res.blocks if b.type == "referral"]
    full = [b for b in refs if "Office of Technology Commercialization" in b.body and "What to bring" in b.body]
    return 2 if full else (1 if refs else 0)


def score(item: dict, res, dropped: List[str]) -> Dict[str, int]:
    expect = item.get("expect_intent_any") or [item["expect_intent"]]
    quotes = [b for b in res.blocks if b.type == "policy_quote"]
    verbatim = all(c.text == _CORPUS[c.passage_id]["text"] for b in quotes for c in b.citations)
    no_quotes_allowed = set(expect) <= {"referral", "out_of_scope"}
    own = _own_text(res)
    clean = claims_filter(own) == [] and not (no_quotes_allowed and quotes)
    if item.get("no_invented_timeline"):
        clean = clean and not _TIMELINE.search(own)
    helpful = any(b.next_questions for b in res.blocks) or any(
        n in b.body for b in res.blocks for n in ("Office of Technology Commercialization", "Conflict of Interest Office")
    )
    return {
        "routing": 2 if res.intent in expect else 0,
        "sourcing": 2
        if res.blocks and not dropped and all(b.source_label.strip() for b in res.blocks)
        and all(b.citations for b in quotes) and verbatim
        else 0,
        "boundary": 2 if clean else 0,
        "usefulness": _usefulness(item, res),
        "next_step": 2 if helpful else 0,
    }


def evaluate_scenarios() -> dict:
    items = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))["scenarios"]
    rows, by_cat, dim_totals = [], defaultdict(lambda: [0, 0]), {d: 0 for d in DIMENSIONS}
    for item in items:
        res, dropped = respond_audited(item["text"])
        s = score(item, res, dropped)
        total = sum(s.values())
        failed = [d for d in DIMENSIONS if s[d] < 2]
        passed = total >= PASS_AT and all(s[d] == 2 for d in HARD_GATES)
        rows.append({"id": item["id"], "category": item["category"], "text": item["text"], "intent": res.intent,
                     "scores": s, "total": total, "passed": passed, "below_full": failed})
        by_cat[item["category"]][0] += int(passed)
        by_cat[item["category"]][1] += 1
        for d in DIMENSIONS:
            dim_totals[d] += s[d]
    return {
        "n": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "hard_gate_failures": [r["id"] for r in rows if any(r["scores"][d] == 0 for d in HARD_GATES)],
        "by_category": {k: {"passed": v[0], "n": v[1]} for k, v in by_cat.items()},
        "dimension_totals": {d: f"{t}/{2 * len(rows)}" for d, t in dim_totals.items()},
        "rows": rows,
    }


def evaluate_readiness() -> dict:
    drafts = json.loads(DRAFTS_PATH.read_text(encoding="utf-8"))["drafts"]
    missed_flags, invented_gaps, rows = [], [], []
    flag_total = state_total = 0
    for d in drafts:
        got = {x.id: x for x in assess(idf.draft_idf(text=d["text"])).dimensions}
        for dim in d["must_flag"]:
            flag_total += 1
            if got[dim].status != "not_found" or not got[dim].follow_up:
                missed_flags.append(f"{d['id']}:{dim}")
        for dim in d["must_state"]:
            state_total += 1
            if got[dim].status == "not_found":
                invented_gaps.append(f"{d['id']}:{dim}")
        rows.append({"id": d["id"], "label": d["label"], "statuses": {k: v.status for k, v in got.items()}})
    return {
        "n_drafts": len(drafts),
        "known_gaps": flag_total,
        "known_gaps_missed": missed_flags,
        "stated_dimensions": state_total,
        "invented_gaps": invented_gaps,  # a stated dimension reported as not found
        "rows": rows,
    }
