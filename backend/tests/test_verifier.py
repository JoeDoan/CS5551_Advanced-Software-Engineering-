import pytest

from app.services.advisor_models import Block
from app.services.policy_service import PolicyCitation
from app.services.verifier import claims_filter, verify

VERDICTS = [
    "Your invention is patentable.",
    "This invention is novel.",
    "Your work is clearly novel.",
    "My idea is obvious, so skip it.",
    "You should file a patent.",
    "You should not publish yet.",
    "You are an inventor on this.",
    "You're not an inventor.",
    "It will be granted.",
    "This is definitely patentable.",
]
GENERAL_EXPLANATIONS = [
    "An invention is novel when it has not already been made public in the form you claim.",
    "In general it asks whether the invention is new, is not an obvious step from what is already known, and is useful.",
    "Inventors are the people who contributed to the idea of the invention.",
    "Whether a particular invention is novel is a judgment made by the technology office.",
    "You can help by writing down what your work does differently.",
]


@pytest.mark.parametrize("text", VERDICTS)
def test_verdicts_about_the_users_own_work_are_flagged(text):
    assert claims_filter(text)


@pytest.mark.parametrize("text", GENERAL_EXPLANATIONS)
def test_general_explanations_are_not_flagged(text):
    assert claims_filter(text) == []


def _cite(text: str) -> PolicyCitation:
    return PolicyCitation(
        passage_id="x#1", source_title="T", source_url="https://example.test", version="v1",
        applies_to="a", section="s", locator="l", text=text, score=5.0,
    )


def test_blocks_without_a_source_label_are_dropped():
    res = verify([Block(type="glossary", source_label=" ", title="t", body="b")])
    assert res.blocks == [] and "no source label" in res.dropped[0]


def test_policy_quotes_need_citations_and_are_exempt_from_the_claims_filter():
    empty = Block(type="policy_quote", source_label="Quoted policy", title="t", body="b")
    assert verify([empty]).blocks == []
    quote = Block(
        type="policy_quote", source_label="Quoted policy", title="t", body="b",
        citations=[_cite("Your invention is patentable if the Board finds it so.")],
    )
    assert verify([quote]).blocks == [quote]  # the policy's own words, not ours


def test_our_own_text_with_a_verdict_is_dropped_even_in_a_follow_up_chip():
    bad_body = Block(type="glossary", source_label="x", title="t", body="Your invention is patentable.")
    bad_chip = Block(type="referral", source_label="x", title="t", body="fine", next_questions=["You should file now"])
    assert verify([bad_body, bad_chip]).blocks == []
