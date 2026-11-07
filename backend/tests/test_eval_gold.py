import json
import sys
from pathlib import Path

import pytest

from app.services import policy_service as ps

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(EVAL_DIR))
import run_eval  # noqa: E402

GOLD = json.loads((EVAL_DIR / "gold_retrieval.json").read_text(encoding="utf-8"))
PASSAGES = json.load(open(ps.CORPUS_PATH, encoding="utf-8"))["passages"]
SOURCES = {p["source_id"] for p in PASSAGES}


# ------------------------------------------------------------------ the gold set itself
def test_gold_set_is_frozen():
    """Edit the gold file only on purpose: then update gold_retrieval.sha256 and say why in the commit."""
    pinned = (EVAL_DIR / "gold_retrieval.sha256").read_text().strip()
    assert run_eval.gold_sha256() == pinned


def test_gold_set_has_the_planned_shape_and_unique_ids():
    assert (len(GOLD["policy"]), len(GOLD["concept"]), len(GOLD["boundary"])) == (18, 6, 6)
    ids = [i["id"] for k in ("policy", "concept", "boundary") for i in GOLD[k]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("item", GOLD["policy"], ids=lambda i: i["id"])
def test_every_policy_item_can_be_satisfied_by_the_corpus(item):
    assert set(item["expect_sources"]) <= SOURCES
    phrase = item.get("expect_phrase")
    if phrase:
        assert any(
            p["source_id"] in item["expect_sources"] and phrase.lower() in p["text"].lower() for p in PASSAGES
        ), "no passage from an expected source contains the phrase"


# ------------------------------------------------------------------ regression floors
def test_retrieval_floors_hold_on_the_gold_set():
    r = run_eval.evaluate_retrieval()
    # Floors, not goals: the numbers recorded in eval/results when the topic boost landed.
    assert r["hit@5"] >= 0.77 and r["mrr"] >= 0.58 and r["false_refusals"] == 0


def test_advisor_boundary_and_concept_items_all_hold():
    a = run_eval.evaluate_advisor()
    assert a["boundary_violations"] == [] and a["concept_failures"] == [] and a["dropped_blocks"] == 0


# ------------------------------------------------------------------ topic boost
@pytest.mark.parametrize(
    "q,family",
    [
        ("Who owns my invention?", "invention"),
        ("Can I patent software?", "invention"),
        ("What happens after I submit a disclosure?", "invention"),  # bare "disclosure" defaults to the form
        ("Do I have to report outside consulting?", "coi"),
        ("I own equity in a company", "coi"),
        ("How often must I update my financial disclosure?", "coi"),  # a financial cue overrides the default
        ("Does an outside sponsor own my results?", None),  # "outside" alone is not a conflict cue
        ("Equity in a startup that wants to license my invention", None),  # both families: no boost
        ("Who pays for parking?", None),
    ],
)
def test_topic_cues(q, family):
    got = ps._topic_sources(ps._terms(q))
    expected = {"invention": ps._INVENTION_SOURCES, "coi": ps._COI_SOURCES, None: frozenset()}[family]
    assert got == expected


def test_the_boost_only_reorders_and_never_lowers_the_floor(monkeypatch):
    q = "What happens after I submit a disclosure?"
    monkeypatch.setattr(ps, "TOPIC_BOOST", 3.0)  # even a heavy boost must not admit weak passages
    boosted = ps.answer_question(q)
    monkeypatch.setattr(ps, "TOPIC_BOOST", 1.0)
    plain = ps.answer_question(q)
    raw = {c.passage_id: c.score for c in plain.citations}
    for c in boosted.citations:
        assert c.score >= ps.MIN_SCORE  # the score shown is the raw BM25 score
        if c.passage_id in raw:
            assert c.score == raw[c.passage_id]
    assert len(boosted.citations) <= ps.MAX_RESULTS
    assert boosted.citations[0].passage_id.split("#")[0] in ps._INVENTION_SOURCES
    assert plain.citations[0].passage_id.split("#")[0] not in ps._INVENTION_SOURCES  # the original failure


def test_off_topic_questions_are_still_refused_with_a_heavy_boost(monkeypatch):
    monkeypatch.setattr(ps, "TOPIC_BOOST", 3.0)
    for q in ("zzqx wibble outside", "What is the best pizza in Kansas City?", "What is the parking policy at Volker campus?"):
        assert not ps.answer_question(q).answered


def test_a_financial_disclosure_question_still_leads_with_conflict_of_interest_sources():
    top = ps.answer_question("What happens if I fail to disclose a financial interest on time?").citations[0]
    assert top.passage_id.split("#")[0] in ps._COI_SOURCES


def test_trade_secrets_are_now_answered_from_the_ip_page_and_still_quoted_verbatim():
    ans = ps.answer_question("What are trade secrets?")
    assert ans.answered and ans.citations[0].passage_id.startswith("umkc-ip#")
    corpus = {p["id"]: p for p in PASSAGES}
    assert all(c.text == corpus[c.passage_id]["text"] for c in ans.citations)
