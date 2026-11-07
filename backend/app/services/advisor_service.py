"""One question in, a list of sourced blocks out.

Order matters and is the whole point of the design:
1. Scope gate. Verdicts, inventorship and legal questions get a referral before anything is
   retrieved, so a retrieval score can never decide whether a boundary holds.
2. Glossary. Definitional questions are explained from the glossary first.
3. Policy search. Everything else is answered with verbatim quoted passages, or says plainly
   that nothing matched.
4. Verifier. Every block names its source and none of our own text passes a verdict.
"""

from typing import List, Tuple

from app.services import glossary_service
from app.services.advisor_models import AdvisorResponse, Block
from app.services.policy_service import answer_question
from app.services.scope_service import (
    Decision,
    Intent,
    SOURCE_REFERRAL,
    about_block,
    classify_intent,
    early_contact_block,
    referral_block,
)
from app.services.verifier import verify

POLICY_CHIPS = ["What is an invention disclosure?", "What is public disclosure?"]


def _glossary_blocks(ids: List[str], with_policy: bool = False) -> List[Block]:
    blocks: List[Block] = []
    for gid in ids:
        entry = glossary_service.get(gid)
        if entry:
            blocks.extend(glossary_service.to_block(entry, with_policy=with_policy))
    return blocks


def _policy_block(question: str):
    ans = answer_question(question)
    if not ans.answered:
        return None, ans
    first = ans.citations[0]
    more = len({c.source_title for c in ans.citations}) - 1
    label = f"Quoted policy: {first.source_title}, {first.version}" + (f" and {more} more source(s)" if more > 0 else "")
    block = Block(
        type="policy_quote",
        source_label=label,
        title="What the written policy says",
        body=f"{ans.message}\n\n{ans.disclaimer}",
        citations=ans.citations,
        next_questions=POLICY_CHIPS,
    )
    return block, ans


def _build(decision: Decision, question: str):
    intent = decision.intent
    if intent in (Intent.VERDICT_SEEKING, Intent.INVENTORSHIP, Intent.LEGAL_JUDGMENT, Intent.PROCESS_TIMELINE):
        return "referral", [referral_block(decision), *_glossary_blocks(decision.related_terms)]
    if intent is Intent.READINESS:
        return "concept", [*_glossary_blocks(decision.related_terms), early_contact_block(decision)]
    if intent is Intent.OUT_OF_SCOPE:
        return "out_of_scope", [about_block()]

    entries = glossary_service.lookup(question)
    if entries:
        blocks: List[Block] = []
        for e in entries:
            blocks.extend(glossary_service.to_block(e, with_policy=len(entries) == 1))
        return "concept", blocks

    block, ans = _policy_block(question)
    if block:
        return "policy", [block]
    return "out_of_scope", [
        Block(
            type="referral",
            source_label=SOURCE_REFERRAL,
            title="Nothing in the loaded policies answers this",
            body=f"{ans.message}\n\nI can still explain terms like novelty, prior art and inventorship.",
            next_questions=["What is prior art?", "What is an invention disclosure?"],
        )
    ]


def respond_audited(question: str) -> Tuple[AdvisorResponse, List[str]]:
    """The response plus the reasons any block was dropped. Tests assert the list stays empty."""
    decision = classify_intent(question)
    intent, blocks = _build(decision, question)
    result = verify(blocks)
    if not result.blocks:  # never return an empty answer; fall back to the safe referral
        return AdvisorResponse(intent="out_of_scope", blocks=[about_block()]), result.dropped
    return AdvisorResponse(intent=intent, blocks=result.blocks), result.dropped


def respond(question: str) -> AdvisorResponse:
    return respond_audited(question)[0]
