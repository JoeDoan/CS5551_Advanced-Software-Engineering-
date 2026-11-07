import json

import pytest

from app.services import policy_service
from app.services.advisor_models import AdvisorRequest, AdvisorResponse, Block, GlossaryEntry
from app.services.advisor_service import respond, respond_audited
from app.services.verifier import claims_filter
from tests.test_commercialization import BASE
from tests.test_scope import CONCEPT, INVENTORSHIP, LEGAL, POLICY, READINESS, VERDICT

CORPUS = {p["id"]: p for p in json.load(open(policy_service.CORPUS_PATH, encoding="utf-8"))["passages"]}
ASK = f"{BASE}/advisor/ask"


def _props(model):
    return set(model.model_json_schema()["properties"])


def _required(model):
    return set(model.model_json_schema().get("required", []))


def test_contract_is_frozen():
    """The frontend builds against these names. Change them only together with the frontend."""
    assert _props(AdvisorRequest) == {"question"}
    assert _props(AdvisorResponse) == {"intent", "blocks"} and _required(AdvisorResponse) == {"intent", "blocks"}
    assert _props(Block) == {"type", "source_label", "title", "body", "citations", "next_questions"}
    assert _required(Block) == {"type", "source_label", "title", "body"}
    assert _props(GlossaryEntry) == {
        "id", "term", "aliases", "plain", "example", "think_about", "related_fields", "related",
        "reviewed_by", "reviewed_on", "source_label",
    }
    schema = AdvisorResponse.model_json_schema()
    assert set(schema["properties"]["intent"]["enum"]) == {"policy", "concept", "referral", "out_of_scope"}
    assert set(schema["$defs"]["Block"]["properties"]["type"]["enum"]) == {"policy_quote", "glossary", "coach", "referral"}


def test_the_retrieval_thresholds_were_not_loosened_to_fix_definitions():
    # Relaxing these makes "zzqx wibble outside" return policy citations. The glossary is the fix.
    assert policy_service.MIN_DISTINCT_TERMS == 2 and policy_service.MIN_SCORE == 4.0


def test_a_patentability_question_is_referred_and_never_answered_with_policy():
    res = respond("Is my invention patentable?")
    assert res.intent == "referral"
    assert res.blocks[0].type == "referral" and "Office of Technology Commercialization" in res.blocks[0].body
    assert all(b.type != "policy_quote" for b in res.blocks)
    assert any(b.type == "glossary" for b in res.blocks)  # still helpful: explains the terms involved


def test_a_definition_question_is_explained_instead_of_refused():
    res = respond("What is a conflict of interest?")
    assert res.intent == "concept"
    assert [b.type for b in res.blocks] == ["glossary", "policy_quote"]
    for c in res.blocks[1].citations:
        assert c.text == CORPUS[c.passage_id]["text"]  # quoted, never paraphrased


def test_policy_questions_are_answered_with_verbatim_quotes():
    res = respond("Who owns an invention I make using university resources?")
    assert res.intent == "policy" and res.blocks[0].type == "policy_quote"
    for c in res.blocks[0].citations:
        assert c.text == CORPUS[c.passage_id]["text"] and c.source_url.startswith("https://") and c.version
    assert "not legal advice" in res.blocks[0].body


@pytest.mark.parametrize("q", ["zzqx wibble outside", "What is the weather in Kansas City?", "hello"])
def test_off_topic_questions_say_so_plainly(q):
    res = respond(q)
    assert res.intent == "out_of_scope" and all(b.type != "policy_quote" for b in res.blocks)


BOUNDARY = VERDICT + INVENTORSHIP + LEGAL


@pytest.mark.parametrize("q", BOUNDARY)
def test_no_referred_question_ever_returns_policy_quotes_or_a_verdict(q):
    res, dropped = respond_audited(q)
    assert res.intent == "referral" and res.blocks[0].type == "referral"
    assert all(b.type != "policy_quote" for b in res.blocks)
    assert claims_filter(" ".join(f"{b.title} {b.body}" for b in res.blocks)) == []
    assert dropped == []


@pytest.mark.parametrize("q", POLICY)
def test_adding_a_verdict_request_to_a_policy_question_removes_the_policy_answer(q):
    res = respond(q + " Also, is it patentable?")
    assert res.intent == "referral" and all(b.type != "policy_quote" for b in res.blocks)


ALL_QUESTIONS = BOUNDARY + READINESS + CONCEPT + POLICY


@pytest.mark.parametrize("q", ALL_QUESTIONS)
def test_every_block_names_its_source_and_nothing_is_silently_dropped(q):
    res, dropped = respond_audited(q)
    assert res.blocks and dropped == [], (q, dropped)  # a dropped block means our own text broke a rule
    for b in res.blocks:
        assert b.source_label.strip()
        if b.type == "policy_quote":
            assert b.citations


def test_readiness_questions_encourage_early_contact_and_never_ask_people_to_wait():
    res = respond("Is my work ready to disclose?")
    assert res.intent == "concept"
    early = [b for b in res.blocks if b.title == "Talk to the office early"]
    assert early and "do not need to wait" in early[0].body


def test_follow_up_chips_are_all_answerable():
    seen = set()
    for q in ALL_QUESTIONS + ["hello", "zzqx wibble outside"]:
        for b in respond(q).blocks:
            seen.update(b.next_questions)
    assert seen
    for chip in sorted(seen):
        res, dropped = respond_audited(chip)
        assert res.intent in ("concept", "policy", "referral") and dropped == [], chip


def test_route_returns_the_contract_shape(client):
    res = client.post(ASK, json={"question": "What is prior art?"})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"intent", "blocks"} and body["intent"] == "concept"
    assert set(body["blocks"][0]) == {"type", "source_label", "title", "body", "citations", "next_questions"}
    assert body["blocks"][0]["source_label"].startswith("General explainer")


def test_route_validation_and_auth(client, monkeypatch):
    assert client.post(ASK, json={"question": "x"}).status_code == 422
    assert client.post(ASK, json={"question": "a" * 601}).status_code == 422
    assert client.post(ASK, json={}).status_code == 422
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post(ASK, json={"question": "What is prior art?"}).status_code == 401
