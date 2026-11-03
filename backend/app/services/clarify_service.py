"""Clarifying questions: a few targeted questions the draft cannot answer for itself.

Deterministic. The questions come from what the draft does and does not state, so the
author is asked only about things that change what they must disclose. The answers feed
the compliance checklist; nothing here is saved.
"""

from typing import Dict, List, Literal

from pydantic import BaseModel

from app.services.idf_service import DraftResponse

MAX_QUESTIONS = 5

YES_NO = [("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")]
FUNDING = [
    ("federal", "Federal (NSF, NIH, DOE, DoD ...)"),
    ("other", "State, industry or foundation"),
    ("none", "No external funding"),
    ("unsure", "Not sure"),
]


class Option(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: Literal["public", "funding", "students", "outside_interest", "course_release", "third_party"]
    text: str
    why: str
    options: List[Option]


class ClarifyResponse(BaseModel):
    questions: List[Question]
    note: str = "Answer what you can. Nothing here is saved or sent anywhere."


def _opts(pairs) -> List[Option]:
    return [Option(value=v, label=label) for v, label in pairs]


def _by_id(draft: DraftResponse) -> Dict[str, object]:
    return {f.id: f for f in draft.fields}


def build_questions(draft: DraftResponse) -> ClarifyResponse:
    fields = _by_id(draft)
    public = fields.get("A2_first_public")
    funding = fields.get("B1_types")

    candidates: List[Question] = []

    if public is not None and public.value:
        public_text = (
            f"Your document mentions “{public.value}”. Was that the first time this work was "
            "shared outside your group (talk, slides, preprint, website, meeting with industry)?"
        )
    else:
        public_text = (
            "Have you presented, published or posted this work publicly yet "
            "(talk, slides, preprint, website, meeting with industry)?"
        )
    candidates.append(Question(
        id="public", text=public_text, options=_opts(YES_NO),
        why="A public disclosure can affect patent rights, especially abroad, and starts a deadline.",
    ))

    if funding is None or not funding.value:
        candidates.append(Question(
            id="funding", text="Did any external funding support this work?",
            options=_opts(FUNDING),
            why="Federal funding adds reporting duties, and funders may hold rights.",
        ))

    candidates.append(Question(
        id="students", text="Did any students (not paid employees) contribute ideas to the invention?",
        options=_opts(YES_NO),
        why="Students' rights to inventions are handled differently from employees'.",
    ))
    candidates.append(Question(
        id="outside_interest",
        text="Do you or a family member have a financial interest in a company that would license or benefit from this work?",
        options=_opts(YES_NO),
        why="Outside financial interests must be disclosed and managed.",
    ))
    candidates.append(Question(
        id="course_release",
        text="Would commercializing this need time away from teaching, such as a course release?",
        options=_opts(YES_NO),
        why="Changes to your teaching load affect the department's schedule.",
    ))
    candidates.append(Question(
        id="third_party",
        text="Were materials, data or collaborators from another organization used to make this work?",
        options=_opts(YES_NO),
        why="Other organizations may have rights under agreements you signed.",
    ))
    return ClarifyResponse(questions=candidates[:MAX_QUESTIONS])
