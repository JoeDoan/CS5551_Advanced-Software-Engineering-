"""Compliance checklist: the author's answers and draft in, cited to-do items out.

Deterministic rule table. Each triggered item says why it appears (from the author's own
answers), lists practical next steps, and carries verbatim policy passages from
policy_service as citations. The tool never states a policy rule in its own words: rule
text comes only from quoted passages. It does not decide whether anything is permitted.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from app.services.idf_service import DraftResponse
from app.services.policy_service import DISCLAIMER, PolicyCitation, answer_question

ECOMPLIANCE_URL = "https://umkc.ecompliance.umsystem.edu/login"
COI_PAGE_URL = "https://ori.umkc.edu/policy-and-forms/conflict-of-interest/"
SUBMIT_PAGE_URL = (
    "https://ori.umkc.edu/facilities-compliance-and-commercialization/commercialization/"
    "process/submit-an-invention-disclosure.php"
)
CITATIONS_PER_ITEM = 2


class Link(BaseModel):
    label: str
    url: str


class ChecklistItem(BaseModel):
    id: str
    title: str
    status: Literal["action", "review"]
    why: str
    actions: List[str]
    links: List[Link]
    citations: List[PolicyCitation]
    tool: Optional[Literal["buyout"]] = None


class ChecklistResponse(BaseModel):
    items: List[ChecklistItem]
    disclaimer: str = DISCLAIMER


class ChecklistRequest(BaseModel):
    draft: DraftResponse
    answers: Dict[str, str] = {}


def _cite(query: str) -> List[PolicyCitation]:
    return answer_question(query).citations[:CITATIONS_PER_ITEM]


def _draft_value(draft: DraftResponse, field_id: str) -> str:
    return next((f.value for f in draft.fields if f.id == field_id), "")


def build_checklist(req: ChecklistRequest) -> ChecklistResponse:
    draft, answers = req.draft, req.answers
    items: List[ChecklistItem] = []

    if answers.get("outside_interest") == "yes":
        items.append(ChecklistItem(
            id="outside_interest", title="Disclose your outside financial interest", status="action",
            why="You said you or a family member has a financial interest in a company that could benefit.",
            actions=[
                "Complete the Conflict of Interest and Conflict of Commitment Disclosure Form in eCompliance.",
                "Say so in section D.2 of the invention disclosure if that company would be a licensee.",
                "Email umkccoi@umkc.edu before you negotiate with the company.",
            ],
            links=[Link(label="eCompliance disclosure", url=ECOMPLIANCE_URL),
                   Link(label="UMKC Conflict of Interest", url=COI_PAGE_URL)],
            citations=_cite("financial interest in a company outside interests disclose conflict"),
        ))

    if answers.get("students") == "yes":
        items.append(ChecklistItem(
            id="students", title="Students who contributed ideas", status="action",
            why="You said students contributed ideas to the invention.",
            actions=[
                "List each such student as a potential inventor in section C.1 and note that they are not a System employee.",
                "Ask the Office of Technology Commercialization about student rights before you assign or promise anything.",
            ],
            links=[Link(label="Submit an invention disclosure", url=SUBMIT_PAGE_URL)],
            citations=_cite("student invention rights enrolled university resources non-assertion"),
        ))

    federal = answers.get("funding") == "federal" or _draft_value(draft, "B1_types") == "Federal"
    if federal:
        items.append(ChecklistItem(
            id="federal_funding", title="Federal funding", status="action",
            why="Your answers or your document indicate federal funding.",
            actions=[
                "Enter the funding source, award number and principal investigator in section B.1.",
                "The invention disclosure form states the TTO must report inventions made with federal funding to the agency.",
            ],
            links=[Link(label="Submit an invention disclosure", url=SUBMIT_PAGE_URL)],
            citations=_cite("federal grant agency investigator financial interest disclosure NSF PHS"),
        ))

    if answers.get("public") in ("yes", "unsure") or _draft_value(draft, "A2_first_public"):
        items.append(ChecklistItem(
            id="public_disclosure", title="Public disclosure and patent timing", status="action",
            why="This work may already have been shared publicly.",
            actions=[
                "Record each public event with its date in sections A.2 and A.3.",
                "Talk to the Office of Technology Commercialization before any further talks, preprints or posts.",
            ],
            links=[Link(label="UMKC guidance on public disclosure", url=SUBMIT_PAGE_URL)],
            citations=[],
        ))

    if answers.get("course_release") == "yes":
        items.append(ChecklistItem(
            id="course_release", title="Course release or change in effort", status="action",
            why="You said commercializing this may need time away from teaching.",
            actions=[
                "Talk to your chair before assuming a release is possible.",
                "Use the simulator below to see what a one-course release would do to the schedule.",
            ],
            links=[Link(label="UMKC Conflict of Interest", url=COI_PAGE_URL)],
            citations=_cite("outside interests must not interfere with University responsibilities commitment time"),
            tool="buyout",
        ))

    if answers.get("third_party") == "yes":
        items.append(ChecklistItem(
            id="third_party", title="Third-party materials and agreements", status="action",
            why="You said another organization's materials, data or collaborators were used.",
            actions=[
                "Fill in section B.2: the agreement types (NDA, collaboration, research, consulting, MOU ...) and the other parties.",
                "Attach copies of the agreements if you have them.",
            ],
            links=[Link(label="Submit an invention disclosure", url=SUBMIT_PAGE_URL)],
            citations=[],
        ))

    items.append(ChecklistItem(
        id="annual_disclosure", title="Check your annual outside-activity disclosure", status="review",
        why="Faculty and exempt staff disclose outside interests every year, and a new venture may change it.",
        actions=["Confirm your latest eCompliance disclosure mentions any consulting or business activity."],
        links=[Link(label="eCompliance disclosure", url=ECOMPLIANCE_URL)],
        citations=_cite("annual report disclosing all outside interests faculty exempt staff"),
    ))
    return ChecklistResponse(items=items)
