#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scores the copilot parser against backend/tests/data/copilot_eval.json.

  python backend/data/scripts/run_copilot_eval.py --parser rules --split heldout
  ANTHROPIC_API_KEY=... python backend/data/scripts/run_copilot_eval.py --parser llm

A case passes when the parsed ScenarioSpec equals the expected one on every field the
copilot controls (see spec_key). 'unsupported' cases must also yield an empty spec and a
warning. Use the dev split while building the parser; run heldout once and report it.
"""

import argparse
import json
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND)

from app.services.copilot_service import (  # noqa: E402
    DEPT_ALIASES,
    Vocabulary,
    parse_prompt,
    spec_key,
)
from app.services.scenario_service import ScenarioSpec  # noqa: E402

DATA = os.path.join(BACKEND, "data", "umkc")
EVAL = os.path.join(BACKEND, "tests", "data", "copilot_eval.json")


def vocabulary_from_json() -> Vocabulary:
    def load(name):
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)

    return Vocabulary(
        instructors=sorted(u["name"] for u in load("users.json") if u.get("role") == "instructor"),
        departments=sorted({c["course_name"].split()[0].upper() for c in load("courses.json")}),
        rooms=sorted(r["room_number"] for r in load("rooms.json")),
    )


def load_cases(split="all"):
    with open(EVAL, encoding="utf-8") as f:
        data = json.load(f)
    cases = data["cases"]
    return [c for c in cases if split == "all" or c["split"] == split]


def expected_spec(case, departments):
    exp = dict(case["expected"])
    if exp.get("enrollment_growth") == "ALL_DEPARTMENTS_10":
        exp["enrollment_growth"] = [{"department": d, "pct": 10} for d in departments]
    return ScenarioSpec(**exp)


def evaluate(cases, vocab, use_llm):
    rows = []
    for case in cases:
        resp = parse_prompt(case["prompt"], vocab, use_llm=use_llm, self_name=case.get("as"))
        want = expected_spec(case, vocab.departments)
        ok = spec_key(resp.spec) == spec_key(want)
        if case.get("unsupported"):
            ok = ok and (not resp.understood) and bool(resp.warnings)
        rows.append({"case": case, "resp": resp, "ok": ok, "want": spec_key(want)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", choices=["rules", "llm"], default="rules")
    ap.add_argument("--split", choices=["dev", "heldout", "all"], default="all")
    args = ap.parse_args()
    vocab = vocabulary_from_json()
    rows = evaluate(load_cases(args.split), vocab, use_llm=args.parser == "llm")
    for r in rows:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"[{mark}] #{r['case']['id']:>2} ({r['case']['split']}, {r['resp'].parser_used}) {r['case']['prompt']}")
        if not r["ok"]:
            print("   expected:", r["want"])
            print("   got:     ", spec_key(r["resp"].spec))
            print("   warnings:", r["resp"].warnings, "| llm_status:", r["resp"].llm_status)
    for split in ("dev", "heldout"):
        sub = [r for r in rows if r["case"]["split"] == split]
        if sub:
            print(f"{split}: {sum(r['ok'] for r in sub)}/{len(sub)} exact-match")
    if args.parser == "llm":
        used = sum(r["resp"].parser_used == "llm" for r in rows)
        print(f"LLM actually used on {used}/{len(rows)} prompts (the rest fell back to rules)")
    _ = DEPT_ALIASES  # keep the import explicit: the alias table is part of what is evaluated


if __name__ == "__main__":
    main()
