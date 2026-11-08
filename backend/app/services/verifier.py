from typing import List, Literal

from pydantic import BaseModel, Field

from app.services.policy_service import PolicyCitation
from app.services.scope_service import (
    REFERRAL_SOURCE_LABEL,
    build_referral_block,
    claims_filter,
)

AdvisorIntent = Literal["policy", "concept", "referral", "out_of_scope"]
AdvisorBlockType = Literal["policy_quote", "glossary", "coach", "referral"]

GLOSSARY_SOURCE_LABEL = (
    "General explainer, draft, not yet reviewed by the technology office"
)
DRAFT_SOURCE_LABEL = "From your draft"
DEFAULT_POLICY_SOURCE_LABEL = "Quoted policy (title, version)"

_DEFAULT_LABEL_BY_TYPE = {
    "policy_quote": DEFAULT_POLICY_SOURCE_LABEL,
    "glossary": GLOSSARY_SOURCE_LABEL,
    "coach": DRAFT_SOURCE_LABEL,
    "referral": REFERRAL_SOURCE_LABEL,
}


class AdvisorBlock(BaseModel):
    type: AdvisorBlockType
    source_label: str
    title: str
    body: str
    citations: List[PolicyCitation] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)


class AdvisorResponse(BaseModel):
    intent: AdvisorIntent
    blocks: List[AdvisorBlock]


def _is_valid_source_label(label: str) -> bool:
    if not label or not label.strip():
        return False
    cleaned = label.strip()
    if cleaned in (
        GLOSSARY_SOURCE_LABEL,
        DRAFT_SOURCE_LABEL,
        REFERRAL_SOURCE_LABEL,
        DEFAULT_POLICY_SOURCE_LABEL,
    ):
        return True
    return cleaned.startswith("Quoted policy (") and cleaned.endswith(")")


def verify(response: AdvisorResponse) -> AdvisorResponse:
    verified_blocks: List[AdvisorBlock] = []
    intent: AdvisorIntent = response.intent

    for block in response.blocks:
        source_label = block.source_label
        if not _is_valid_source_label(source_label):
            source_label = _DEFAULT_LABEL_BY_TYPE.get(
                block.type, REFERRAL_SOURCE_LABEL
            )

        if not claims_filter(f"{block.title} {block.body}"):
            ref = build_referral_block("verdict_seeking", "")
            verified_blocks.append(AdvisorBlock(**ref))
            intent = "referral"
            continue

        verified_blocks.append(
            block.model_copy(update={"source_label": source_label})
        )

    if not verified_blocks:
        ref = build_referral_block("out_of_scope", "")
        verified_blocks.append(AdvisorBlock(**ref))
        if intent not in ("referral", "out_of_scope"):
            intent = "out_of_scope"

    return AdvisorResponse(intent=intent, blocks=verified_blocks)
