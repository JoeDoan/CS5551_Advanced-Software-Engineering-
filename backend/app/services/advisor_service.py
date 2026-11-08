from typing import Dict, List, Optional

from app.services import (
    glossary_service,
    policy_service,
    readiness_service,
    scope_service,
    verifier,
)
from app.services.idf_service import DraftResponse
from app.services.verifier import (
    DEFAULT_POLICY_SOURCE_LABEL,
    DRAFT_SOURCE_LABEL,
    AdvisorBlock,
    AdvisorBlockType,
    AdvisorIntent,
    AdvisorResponse,
)

__all__ = [
    "AdvisorBlock",
    "AdvisorBlockType",
    "AdvisorIntent",
    "AdvisorResponse",
    "respond",
]

_CONCEPT_FOLLOW_UPS: Dict[str, List[str]] = {
    "novelty": [
        "What does prior art mean for a faculty manuscript?",
        "What counts as a public disclosure before filing a patent?",
    ],
    "prior art": [
        "What does novelty mean in an invention disclosure?",
        "What happens after I submit an invention disclosure?",
    ],
    "inventorship": [
        "What are the conditions for enrolled students to assign inventions to the university?",
        "Who owns an invention I make using university resources?",
    ],
    "public disclosure": [
        "What happens after I submit an invention disclosure?",
        "What does prior art mean for a faculty manuscript?",
    ],
    "development stage": [
        "What does translational readiness mean?",
        "What is a potential application?",
    ],
    "translational readiness": [
        "What does development stage mean?",
        "What does differentiation mean?",
    ],
    "potential application": [
        "What does differentiation mean?",
        "What does translational readiness mean?",
    ],
    "differentiation": [
        "What does novelty mean in an invention disclosure?",
        "What does prior art mean for a faculty manuscript?",
    ],
    "conflict of interest": [
        "Do I have to disclose consulting for a company every year?",
        "What is the dollar threshold for a significant financial interest on a federal grant?",
    ],
    "invention disclosure": [
        "What happens after I submit an invention disclosure?",
        "Who owns an invention I make using university resources?",
    ],
    "licence": [
        "How are net proceeds from licensing a patented invention shared with inventors?",
        "Can the university waive or reassign rights in an invention back to the inventor?",
    ],
    "equity": [
        "Do I have to disclose consulting for a company every year?",
        "What is a conflict of interest?",
    ],
}

_POLICY_FOLLOW_UPS: List[str] = [
    "What happens after I submit an invention disclosure?",
    "What is a conflict of interest?",
]


def _policy_source_label(citations: list) -> str:
    if citations:
        first = citations[0]
        return f"Quoted policy ({first.source_title}, {first.version})"
    return DEFAULT_POLICY_SOURCE_LABEL


def respond(
    question: str,
    draft: Optional[DraftResponse] = None,
) -> AdvisorResponse:
    raw_intent = scope_service.classify_intent(question)

    if raw_intent in ("verdict_seeking", "inventorship", "legal_judgment"):
        ref_dict = scope_service.build_referral_block(raw_intent, question)
        return verifier.verify(
            AdvisorResponse(
                intent="referral",
                blocks=[AdvisorBlock(**ref_dict)],
            )
        )

    if raw_intent == "concept":
        entry = glossary_service.lookup(question)
        if entry is not None:
            term_key = entry.term.lower()
            next_qs = _CONCEPT_FOLLOW_UPS.get(
                term_key,
                [
                    "Who owns an invention I make using university resources?",
                    "What happens after I submit an invention disclosure?",
                ],
            )
            blocks: List[AdvisorBlock] = [
                AdvisorBlock(
                    type="glossary",
                    source_label=entry.source_label,
                    title=entry.term,
                    body=(
                        f"{entry.plain} "
                        f"Example: {entry.example} "
                        f"What the office asks: {entry.what_office_asks}"
                    ),
                    citations=[],
                    next_questions=next_qs,
                )
            ]

            policy_ans = policy_service.answer_question(question)
            if policy_ans.answered and policy_ans.citations:
                blocks.append(
                    AdvisorBlock(
                        type="policy_quote",
                        source_label=_policy_source_label(policy_ans.citations),
                        title="Related policy passages",
                        body=policy_ans.message,
                        citations=policy_ans.citations,
                        next_questions=[],
                    )
                )

            if draft is not None and term_key in (
                "translational readiness",
                "development stage",
                "potential application",
                "differentiation",
            ):
                assessed = readiness_service.assess(draft, "")
                gaps = [
                    d.id for d in assessed.dimensions if d.status != "stated"
                ]
                gap_summary = (
                    f"Dimensions not yet stated in your current draft: {', '.join(gaps)}."
                    if gaps
                    else "All six readiness dimensions have initial quotes in your current draft."
                )
                blocks.append(
                    AdvisorBlock(
                        type="coach",
                        source_label=DRAFT_SOURCE_LABEL,
                        title="Readiness snapshot from your draft",
                        body=f"{gap_summary} {assessed.note}",
                        citations=[],
                        next_questions=[],
                    )
                )

            return verifier.verify(AdvisorResponse(intent="concept", blocks=blocks))

    if raw_intent == "policy":
        ans = policy_service.answer_question(question)
        if ans.answered and ans.citations:
            block = AdvisorBlock(
                type="policy_quote",
                source_label=_policy_source_label(ans.citations),
                title="Quoted policy passages",
                body=ans.message,
                citations=ans.citations,
                next_questions=_POLICY_FOLLOW_UPS,
            )
            return verifier.verify(AdvisorResponse(intent="policy", blocks=[block]))

    ref_dict = scope_service.build_referral_block("out_of_scope", question)
    return verifier.verify(
        AdvisorResponse(
            intent="out_of_scope",
            blocks=[AdvisorBlock(**ref_dict)],
        )
    )
