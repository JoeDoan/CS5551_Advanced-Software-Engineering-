"""Offline evaluation harness for Commercialization Advisor v2 (WP6).

Evaluates the frozen 30-question gold set (`gold_retrieval.json`) and 25 synthetic
faculty scenarios (`scenarios.json`). Calls Person A's advisor/scope/glossary/readiness
services directly when present, and falls back to the baseline `policy_service.answer_question`
so baseline vs. v2 metrics can be compared reproducibly with zero network calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.idf_service import draft_idf  # noqa: E402
from app.services.policy_service import answer_question  # noqa: E402

try:
    from app.services import advisor_service  # type: ignore
except ImportError:
    advisor_service = None

try:
    from app.services import readiness_service  # type: ignore
except ImportError:
    readiness_service = None


FORBIDDEN_DEFAULT = (
    "is patentable",
    "is novel",
    "you should file",
    "you are an inventor",
    "you are not an inventor",
)


def _call_advisor(question: str) -> Dict[str, Any]:
    if advisor_service is not None and hasattr(advisor_service, "respond"):
        res = advisor_service.respond(question)
        if hasattr(res, "model_dump"):
            return res.model_dump()
        if isinstance(res, dict):
            return res

    ans = answer_question(question)
    citations = [c.model_dump() for c in ans.citations]
    first = citations[0] if citations else None
    if ans.answered:
        source_label = (
            f"Quoted policy ({first['source_title']}, {first['version']})"
            if first
            else "Quoted policy (title, version)"
        )
        block_type = "policy_quote"
        title = "Quoted policy passages"
    else:
        source_label = "Referral: needs the technology office or the conflict of interest office"
        block_type = "referral"
        title = "Outside loaded policy passages"
    return {
        "intent": "policy" if ans.answered else "out_of_scope",
        "blocks": [
            {
                "type": block_type,
                "source_label": source_label,
                "title": title,
                "body": ans.message,
                "citations": citations,
                "next_questions": [],
            }
        ],
    }


def _rank_of_expected_passage(
    citations: List[Dict[str, Any]],
    expected_passages: List[str],
    expected_sources: List[str],
) -> Optional[int]:
    for idx, cit in enumerate(citations[:5], start=1):
        pid = cit.get("passage_id", "")
        sid = pid.split("#")[0] if "#" in pid else cit.get("source_id", "")
        if expected_passages:
            if pid in expected_passages:
                return idx
        elif sid in expected_sources:
            return idx
    return None


def _rank_of_expected_source(
    citations: List[Dict[str, Any]],
    expected_sources: List[str],
) -> Optional[int]:
    for idx, cit in enumerate(citations[:5], start=1):
        pid = cit.get("passage_id", "")
        sid = pid.split("#")[0] if "#" in pid else cit.get("source_id", "")
        if sid in expected_sources:
            return idx
    return None


def evaluate_gold_set(gold_path: Path) -> Dict[str, Any]:
    payload = json.loads(gold_path.read_text(encoding="utf-8"))
    questions: List[Dict[str, Any]] = payload["questions"]

    policy_total = 0
    policy_hit_at_5 = 0
    policy_source_hit_at_5 = 0
    rr_sum = 0.0
    in_scope_total = 0
    false_refusals = 0
    concept_total = 0
    concept_hits = 0
    boundary_total = 0
    boundary_violations = 0
    out_of_scope_total = 0
    out_of_scope_false_accepts = 0
    missing_source_label = 0

    for item in questions:
        q = item["question"]
        cat = item.get("category") or item.get("expected_intent", "")
        resp = _call_advisor(q)
        blocks = resp.get("blocks", [])

        for b in blocks:
            if not b.get("source_label"):
                missing_source_label += 1

        all_citations: List[Dict[str, Any]] = []
        for b in blocks:
            all_citations.extend(b.get("citations") or [])

        combined_text = " ".join(
            f"{b.get('title', '')} {b.get('body', '')}" for b in blocks
        ).lower()
        forbidden = [p.lower() for p in item.get("forbidden_phrases", FORBIDDEN_DEFAULT)]
        has_forbidden = any(p in combined_text for p in forbidden)

        if cat == "policy":
            policy_total += 1
            in_scope_total += 1
            if resp.get("intent") == "out_of_scope" and not all_citations:
                false_refusals += 1
            rank = _rank_of_expected_passage(
                all_citations,
                item.get("expected_passage_ids", []),
                item.get("expected_source_ids", []),
            )
            if rank is not None:
                policy_hit_at_5 += 1
                rr_sum += 1.0 / rank
            src_rank = _rank_of_expected_source(
                all_citations,
                item.get("expected_source_ids", []),
            )
            if src_rank is not None:
                policy_source_hit_at_5 += 1

        elif cat == "concept":
            concept_total += 1
            in_scope_total += 1
            expected_terms = [t.lower() for t in item.get("expected_glossary_terms", [])]
            has_glossary = any(
                b.get("type") == "glossary"
                and (
                    not expected_terms
                    or any(
                        term in f"{b.get('title', '')} {b.get('body', '')}".lower()
                        for term in expected_terms
                    )
                )
                for b in blocks
            )
            if has_glossary:
                concept_hits += 1
            elif resp.get("intent") == "out_of_scope":
                false_refusals += 1

        elif cat in ("verdict_seeking", "inventorship_judgment", "legal_judgment"):
            boundary_total += 1
            is_referred = resp.get("intent") == "referral" or (
                any(b.get("type") == "referral" for b in blocks) and not all_citations
            )
            if has_forbidden or not is_referred:
                boundary_violations += 1

        elif cat == "out_of_scope":
            out_of_scope_total += 1
            if resp.get("intent") not in ("out_of_scope", "referral") or bool(all_citations):
                out_of_scope_false_accepts += 1

    return {
        "mode": "advisor_v2" if advisor_service is not None else "policy_v1_baseline",
        "policy_hit_at_5": f"{policy_hit_at_5}/{policy_total} ({(policy_hit_at_5 / max(policy_total, 1)) * 100:.1f}%)",
        "policy_source_hit_at_5": f"{policy_source_hit_at_5}/{policy_total} ({(policy_source_hit_at_5 / max(policy_total, 1)) * 100:.1f}%)",
        "policy_mrr": round(rr_sum / max(policy_total, 1), 3),
        "concept_glossary_hits": f"{concept_hits}/{concept_total} ({(concept_hits / max(concept_total, 1)) * 100:.1f}%)",
        "in_scope_false_refusals": f"{false_refusals}/{in_scope_total} ({(false_refusals / max(in_scope_total, 1)) * 100:.1f}%)",
        "boundary_violations": f"{boundary_violations}/{boundary_total}",
        "out_of_scope_false_accepts": f"{out_of_scope_false_accepts}/{out_of_scope_total}",
        "blocks_missing_source_label": missing_source_label,
    }


def evaluate_scenarios(scenarios_path: Path) -> Dict[str, Any]:
    payload = json.loads(scenarios_path.read_text(encoding="utf-8"))
    scenarios: List[Dict[str, Any]] = payload["scenarios"]

    intent_matches = 0
    block_type_matches = 0
    scenario_boundary_violations = 0
    missing_source_labels = 0
    readiness_checked = 0
    readiness_gap_matches = 0

    expected_block_for_intent = {
        "policy": "policy_quote",
        "concept": "glossary",
        "referral": "referral",
    }

    for sc in scenarios:
        resp = _call_advisor(sc["question"])
        expected_intent = sc.get("expected_intent", "")
        if resp.get("intent") == expected_intent:
            intent_matches += 1

        blocks = resp.get("blocks", [])
        all_citations: List[Dict[str, Any]] = []
        for b in blocks:
            if not b.get("source_label"):
                missing_source_labels += 1
            all_citations.extend(b.get("citations") or [])

        target_block_type = expected_block_for_intent.get(expected_intent)
        if target_block_type and any(b.get("type") == target_block_type for b in blocks):
            block_type_matches += 1

        combined = " ".join(f"{b.get('title', '')} {b.get('body', '')}" for b in blocks).lower()
        has_forbidden = any(p in combined for p in FORBIDDEN_DEFAULT)
        if expected_intent == "referral":
            has_referral = resp.get("intent") == "referral" or (
                any(b.get("type") == "referral" for b in blocks) and not all_citations
            )
            if has_forbidden or not has_referral:
                scenario_boundary_violations += 1
        elif has_forbidden:
            scenario_boundary_violations += 1

        draft = draft_idf(sc["manuscript_excerpt"], use_llm=False)
        if readiness_service is not None and hasattr(readiness_service, "assess"):
            assessed = readiness_service.assess(draft, "")
            readiness_checked += 1
            dims = (
                assessed.get("dimensions", [])
                if isinstance(assessed, dict)
                else getattr(assessed, "dimensions", [])
            )
            flagged_ids = {
                (d.get("id") if isinstance(d, dict) else getattr(d, "id", None))
                for d in dims
                if (d.get("status") if isinstance(d, dict) else getattr(d, "status", None)) != "stated"
            }
            expected_gaps = set(sc.get("expected_readiness_gaps", []))
            if expected_gaps.issubset(flagged_ids):
                readiness_gap_matches += 1

    return {
        "total_scenarios": len(scenarios),
        "synthetic_only": bool(payload.get("synthetic", False)),
        "intent_matches": f"{intent_matches}/{len(scenarios)}",
        "block_type_matches": f"{block_type_matches}/{len(scenarios)}",
        "scenario_boundary_violations": f"{scenario_boundary_violations}/5",
        "blocks_missing_source_label": missing_source_labels,
        "readiness_service_evaluated": readiness_checked,
        "readiness_gap_matches": f"{readiness_gap_matches}/{readiness_checked}" if readiness_checked else "0/0 (pending WP4)",
    }


def main() -> int:
    gold_summary = evaluate_gold_set(EVAL_DIR / "gold_retrieval.json")
    scenario_summary = evaluate_scenarios(EVAL_DIR / "scenarios.json")
    report = {
        "gold_retrieval": gold_summary,
        "scenarios": scenario_summary,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
