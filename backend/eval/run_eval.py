"""Run the frozen gold set against the advisor. Offline, deterministic, no network, no model.

    python eval/run_eval.py                 # print the table
    python eval/run_eval.py --out FILE      # also write a JSON run record

Retrieval items are scored on the raw policy search (what the topic boost changes). Concept and
boundary items are scored on the full advisor. The record carries the code and corpus state so
two runs can be compared honestly. It logs only the gold questions.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import policy_service  # noqa: E402
from app.services.advisor_service import respond_audited  # noqa: E402

GOLD_PATH = Path(__file__).resolve().parent / "gold_retrieval.json"
K = 5


def gold_sha256() -> str:
    """Hash of the gold file with line endings normalised, so a CRLF checkout does not change it."""
    normalised = GOLD_PATH.read_bytes().replace(bytes([13, 10]), bytes([10]))
    return hashlib.sha256(normalised).hexdigest()


def _gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def _source_of(passage_id: str) -> str:
    return passage_id.split("#")[0]


def _is_hit(item: dict, citation) -> bool:
    if _source_of(citation.passage_id) not in item["expect_sources"]:
        return False
    phrase = item.get("expect_phrase")
    return phrase is None or phrase.lower() in citation.text.lower()


def evaluate_retrieval() -> dict:
    rows = []
    for item in _gold()["policy"]:
        ans = policy_service.answer_question(item["question"])
        ranks = [i for i, c in enumerate(ans.citations[:K], start=1) if _is_hit(item, c)]
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "answered": ans.answered,
                "first_hit_rank": ranks[0] if ranks else None,
                "top_sources": [_source_of(c.passage_id) for c in ans.citations[:K]],
            }
        )
    n = len(rows)
    hits = [r for r in rows if r["first_hit_rank"] is not None]
    return {
        "n": n,
        f"hit@{K}": round(len(hits) / n, 3),
        "hit@1": round(sum(1 for r in hits if r["first_hit_rank"] == 1) / n, 3),
        "mrr": round(sum(1 / r["first_hit_rank"] for r in hits) / n, 3),
        "false_refusals": sum(1 for r in rows if not r["answered"]),
        "rows": rows,
    }


def evaluate_advisor() -> dict:
    gold = _gold()
    concept_fail, boundary_fail, dropped_blocks = [], [], 0
    for item in gold["concept"]:
        res, dropped = respond_audited(item["question"])
        dropped_blocks += len(dropped)
        if res.intent != item["expect_intent"] or res.blocks[0].type != "glossary":
            concept_fail.append(item["id"])
    for item in gold["boundary"]:
        res, dropped = respond_audited(item["question"])
        dropped_blocks += len(dropped)
        if res.intent != item["expect_intent"] or any(b.type == "policy_quote" for b in res.blocks):
            boundary_fail.append(item["id"])
    return {
        "concept_n": len(gold["concept"]),
        "concept_failures": concept_fail,
        "boundary_n": len(gold["boundary"]),
        "boundary_violations": boundary_fail,  # a verdict-seeking question that got policy quotes
        "dropped_blocks": dropped_blocks,
    }


def manifest() -> Dict[str, object]:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=BACKEND, timeout=10
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        sha = ""
    return {
        "git_head": sha or "unknown",
        "gold_sha256": gold_sha256(),
        "corpus_passages": len(json.loads(policy_service.CORPUS_PATH.read_text(encoding="utf-8"))["passages"]),
        "min_score": policy_service.MIN_SCORE,
        "min_distinct_terms": policy_service.MIN_DISTINCT_TERMS,
        "topic_boost": getattr(policy_service, "TOPIC_BOOST", None),
    }


def run() -> dict:
    return {"manifest": manifest(), "retrieval": evaluate_retrieval(), "advisor": evaluate_advisor()}


def _print(record: dict) -> None:
    r, a, m = record["retrieval"], record["advisor"], record["manifest"]
    print(f"gold {m['gold_sha256'][:12]}  corpus {m['corpus_passages']}  boost {m['topic_boost']}")
    print(f"retrieval  n={r['n']}  Hit@{K}={r[f'hit@{K}']}  Hit@1={r['hit@1']}  MRR={r['mrr']}  false refusals={r['false_refusals']}")
    for row in r["rows"]:
        mark = "ok " if row["first_hit_rank"] else "MISS"
        print(f"  {mark} {row['id']} rank={row['first_hit_rank']}  {row['question']}")
    print(f"concept    {a['concept_n'] - len(a['concept_failures'])}/{a['concept_n']}  failures={a['concept_failures']}")
    print(f"boundary   violations={a['boundary_violations']} of {a['boundary_n']}  dropped blocks={a['dropped_blocks']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="write the run record as JSON")
    args = parser.parse_args()
    result = run()
    _print(result)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
