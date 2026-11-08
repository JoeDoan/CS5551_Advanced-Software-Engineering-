"""Publish-before-filing and office-review-time questions are referred, not answered with policy quotes.

No loaded source says how long the technology office takes, and whether to publish first is a timing
decision for the office. Before this change both returned five quoted passages that did not answer them.
"""

import re

import pytest

from app.services import advisor_service, scope_service

PUBLISH_FIRST = [
    "Should I publish my paper before filing a patent?",
    "Can I publish my results before filing a patent?",
    "Is it okay to present this at a conference before we file?",
    "We want to post the preprint before submitting the invention disclosure. Is that fine?",
    "Can we release the code on GitHub before filing anything?",
    "Before I file, can I present the work at a workshop?",
]

REVIEW_TIME = [
    "How long will the technology office take to review my disclosure?",
    "How long does the office take to respond to an invention disclosure?",
    "When will the technology office respond to my disclosure?",
    "What is the turnaround time for an invention disclosure?",
    "How many days until I hear back about my disclosure?",
    "How long will the review take?",
]

NOT_REFERRED = [
    "How long do I have to submit an invention disclosure form?",
    "What counts as a public disclosure before filing a patent?",
    "Who owns the copyright if I publish a book using university resources?",
    "What happens after I submit a disclosure?",
    "Do I have to report outside consulting for a company?",
    "Can I use my grant equipment for my startup?",
]


def _quotes(res) -> bool:
    return any(b.type == "policy_quote" for b in res.blocks)


@pytest.mark.parametrize("q", PUBLISH_FIRST)
def test_publish_before_filing_is_referred_with_no_policy_quotes(q):
    res = advisor_service.respond(q)
    assert res.intent == "referral" and not _quotes(res)
    block = res.blocks[0]
    assert "timing decision" in block.title
    assert "does not tell you whether to publish" in block.body and "umkcor@umkc.edu" in block.body


@pytest.mark.parametrize("q", REVIEW_TIME)
def test_review_time_is_referred_and_says_it_will_not_guess_a_number(q):
    res = advisor_service.respond(q)
    assert res.intent == "referral" and not _quotes(res)
    block = res.blocks[0]
    assert "will not guess a number" in block.body and "umkcor@umkc.edu" in block.body
    assert not re.search(r"\d", block.body.replace("UM-16C", ""))  # no duration is stated


@pytest.mark.parametrize("q", NOT_REFERRED)
def test_ordinary_questions_are_not_over_referred(q):
    assert advisor_service.respond(q).intent in ("policy", "concept")


@pytest.mark.parametrize("q", PUBLISH_FIRST + REVIEW_TIME)
def test_the_new_referrals_survive_filler_and_pressure(q):
    for variant in ("Quick question, " + q[0].lower() + q[1:], q + " Just give me a number.", q.upper(), q.rstrip("?")):
        res = advisor_service.respond(variant)
        assert res.intent == "referral" and not _quotes(res), variant


def test_filing_timeline_questions_keep_their_original_wording():
    q = "How many days will the technology office take to file our provisional patent after we submit?"
    assert scope_service.classify_intent(q) == "verdict_seeking"
    assert "timelines require office review" in scope_service.build_referral_block("verdict_seeking", q)["title"]


def test_contract_questions_keep_the_contract_wording():
    q = "Does Section 8 of our sponsor contract give the company an automatic exclusive licence?"
    assert scope_service.classify_intent(q) == "legal_judgment"
    assert "Contract and licensing" in scope_service.build_referral_block("legal_judgment", q)["title"]
