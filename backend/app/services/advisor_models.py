"""The frozen JSON contract for the commercialization advisor.

These models are the source of truth the frontend builds against. Changing a field name,
a block type or a required field is a breaking change: update tests/test_advisor.py
(test_contract_is_frozen) and tell the frontend owner in the same change.
"""

from typing import List, Literal

from pydantic import BaseModel, Field

from app.services.policy_service import MAX_QUESTION_CHARS, PolicyCitation

BlockType = Literal["policy_quote", "glossary", "coach", "referral"]
IntentName = Literal["policy", "concept", "referral", "out_of_scope"]


class AdvisorRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=MAX_QUESTION_CHARS)


class Block(BaseModel):
    """One piece of an answer. Every block says where it came from.

    glossary: body is the plain-language explanation and an example, separated by a blank
    line; next_questions holds the "think about" prompts.
    policy_quote: citations hold the verbatim passages; body is a short framing line.
    referral: body says who can help and what to bring.
    coach: reserved for the readiness coach (not produced by /advisor/ask).
    """

    type: BlockType
    source_label: str
    title: str
    body: str
    citations: List[PolicyCitation] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)


class AdvisorResponse(BaseModel):
    intent: IntentName
    blocks: List[Block]


class GlossaryEntry(BaseModel):
    """GET /commercialization/glossary returns a list of these."""

    id: str
    term: str
    aliases: List[str]
    plain: str
    example: str
    think_about: List[str]
    related_fields: List[str]
    related: List[str]
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    source_label: str
