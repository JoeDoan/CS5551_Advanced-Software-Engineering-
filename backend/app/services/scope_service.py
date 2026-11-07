"""Decide what kind of question this is before anything is retrieved or written.

The advisor explains concepts and quotes policy. It does not judge whether work is
patentable or novel, who is an inventor, or what someone should file, sign or publish.
Those go to the technology office. This module is plain rules so the boundary does not
depend on a model's mood, and so it can be tested phrase by phrase.

A rule set cannot be proven complete. The tests in tests/test_scope.py show it holds on
the phrasings we thought of, including pressure variants. New phrasings that slip through
get added there first.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from app.services.advisor_models import Block
from app.services.idf_service import _catalogue

SOURCE_REFERRAL = "Referral: needs the technology office or the conflict of interest office"
SOURCE_ABOUT = "About this advisor"

# Same contact the policy answers already give (policy_service.DISCLAIMER). Kept in step by a test.
COI_CONTACT = "UMKC Conflict of Interest Office (umkccoi@umkc.edu)"


class Intent(str, Enum):
    POLICY = "policy"  # default: search the quoted policy corpus
    CONCEPT = "concept"  # "what is X", "define X": explain from the glossary
    READINESS = "readiness"  # "is my work ready", "when should I disclose"
    VERDICT_SEEKING = "verdict_seeking"  # patentable, novel, worth patenting, is it an invention
    INVENTORSHIP = "inventorship"  # who is or should be named an inventor
    LEGAL_JUDGMENT = "legal_judgment"  # should I file/sign/publish, legal advice, rule overrides
    PROCESS_TIMELINE = "process_timeline"  # how long the office takes: no loaded source says, so refer
    OUT_OF_SCOPE = "out_of_scope"  # greetings and the like


@dataclass
class Decision:
    intent: Intent
    related_terms: List[str] = field(default_factory=list)  # glossary ids worth showing beside a referral
    timing: bool = False  # the question is about publishing or presenting before protection
    coi: bool = False  # the question touches outside interests


_DEFINITIONAL = re.compile(
    r"^\s*(?:what(?:'s|\s+is|\s+are|\s+does|\s+do)|define|explain|meaning\s+of|tell\s+me\s+about|describe|difference\s+between)\b",
    re.I,
)
_PERSONAL = re.compile(r"\b(?:my|our|mine|me|i|i'm|i've|we|we're|this|it's|its|that's|their|his|her)\b", re.I)
_POLITE_ME = re.compile(r"\b(?:for|to)\s+me\b|\b(?:tell|show|help|let)\s+me\b", re.I)
_GREETING = re.compile(r"^\s*(?:hi|hello|hey|thanks|thank\s+you|good\s+(?:morning|afternoon|evening))\b[\s!.?,]*$", re.I)

# Politeness in front of a question ("Quick question, ...") must not change how it is read.
_FILLER_LEAD = re.compile(
    r"^\s*(?:hi|hello|hey|please|thanks|thank\s+you|quick\s+question|one\s+question|sorry(?:\s+to\s+bother\s+you)?|"
    r"excuse\s+me|i\s+have\s+a\s+question|just\s+wondering|i\s+was\s+wondering(?:\s+(?:if|whether))?|"
    r"can\s+i\s+ask(?:\s+a\s+question)?)\b[\s,:;!.\-]*(?:but\s+)?",
    re.I,
)

# A request to explain a term, wherever it sits in the question ("... What does that mean?").
MEANING_REQUEST = re.compile(
    r"\b(?:what(?:'s|\s+is|\s+are|\s+does|\s+do)\b[^?.!]{0,80}\b(?:mean|means|meaning|stand\s+for)\b"
    r"|(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:explain|define|describe|clarify)\b"
    r"|tell\s+me\s+what\s+(?:[\w'-]+\s+){0,4}?(?:is|are|means?)\b|(?:explain|define|describe)\s+\w"
    r"|i(?:'m|\s+am)\s+not\s+sure\s+what\b|difference\s+between\b)",
    re.I,
)


def strip_filler(text: str) -> str:
    q = " ".join((text or "").split())  # also collapses runs of spaces, which would stretch the gaps in the rules below
    for _ in range(4):
        m = _FILLER_LEAD.match(q)
        if not m or m.end() == 0:
            break
        q = q[m.end():]
    return q.strip()


_CLAUSE_BREAK = re.compile(r"[?.!;]\s+|\b(?:also|then|plus)\b[\s,]*", re.I)


def _after_first_sentence(q: str) -> str:
    """What follows the first clause, so a definition cannot hide a second, different request."""
    m = _CLAUSE_BREAK.search(q)
    return q[m.end():] if m else ""



_VERDICT = [
    re.compile(r"\bpatentab", re.I),
    re.compile(r"\bcan\s+(?:this|it|that|my\s+\w+|our\s+\w+)\s+be\s+patented\b", re.I),
    re.compile(r"\b(?:possible|able|eligible|allowed)\b.{0,15}\bto\s+patent\b", re.I),
    re.compile(r"\b(?:can|could|will|would)\s+(?:i|we)\s+(?:get\s+)?(?:a\s+)?patent\b", re.I),
    re.compile(
        r"\bis\s+(?:it|this|that|my\s+\w+|our\s+\w+)\s+(?:\w+\s+){0,2}"
        r"(?:novel|inventive|obvious|valuable|worth\b|commercial\w*|marketable|an\s+invention|a\s+real\s+invention)",
        re.I,
    ),
    re.compile(r"\bis\s+(?:it|this|that|my\s+\w+|our\s+\w+)\s+(?:really\s+)?(?:new|original)\s*(?:[?.!]|$)", re.I),
    re.compile(r"\bdo\s+(?:i|we)\s+have\s+(?:an?\s+)?(?:real\s+)?invention\b", re.I),
    re.compile(r"\bworth\s+(?:patenting|filing|commerciali\w+|licens\w+|anything|money)\b", re.I),
    re.compile(r"\bhow\s+much\s+(?:is|will|would|could)\b.{0,40}\b(?:worth|make|earn)\b", re.I),
    re.compile(r"\b(?:novel|new|original|inventive|unique|innovative)\s+enough\b|\benough\s+to\s+(?:patent|file|protect)\b", re.I),
    re.compile(
        r"\b(?:if|whether|think|say|believe)\s+(?:that\s+)?(?:it|this|that|my\s+\w+|our\s+\w+)\s+(?:is|are|seems?)\s+"
        r"(?:\w+\s+){0,2}(?:novel|inventive|obvious|new|original|unique|valuable|worth\w*)\b",
        re.I,
    ),
    re.compile(r"\bwill\s+(?:they|the\s+(?:university|office|patent\s+office|uspto))\s+(?:grant|approve|accept|patent|file)\b", re.I),
]

_INVENTORSHIP = [
    re.compile(r"\bwho\s+(?:is|are|counts?|qualif\w+|should\s+be|gets?\s+to\s+be|would\s+be)\b.{0,40}\binventors?\b", re.I),
    re.compile(r"\bam\s+i\b.{0,20}\b(?:co-?)?inventor", re.I),
    re.compile(r"\b(?:is|are)\s+.{0,35}\b(?:an?|the)\s+(?:co-?)?inventors?\b", re.I),
    re.compile(
        r"\b(?:list|name|add|include|put|credit|remove|exclude)\w*\b.{0,35}\bas\s+(?:an?\s+|the\s+)?(?:co-?)?inventors?\b", re.I
    ),
    re.compile(r"\binventorship\b", re.I),
]

_LEGAL = [
    re.compile(r"\bshould\s+(?:i|we)\s+(?:not\s+)?(?:file|patent|publish|sign|license|sell|share|post|present|submit|accept|negotiate|hire|sue)\b", re.I),
    re.compile(r"\b(?:legal\s+(?:advice|counsel)|lawyer|attorney|sue|lawsuit|infring\w+|liab\w+|illegal|legally)\b", re.I),
    re.compile(r"\bis\s+it\s+legal\b", re.I),
]
_OVERRIDE = [
    re.compile(r"\b(?:ignore|forget|disregard|override|bypass)\b.{0,30}\b(?:rules?|instructions?|guidelines?|restrictions?|limits?|polic(?:y|ies)|above)\b", re.I),
    re.compile(r"\bpretend\b", re.I),
    re.compile(r"\bact\s+as\s+(?:a\s+|my\s+)?(?:lawyer|attorney|patent)", re.I),
]
_TIMING = re.compile(
    r"\b(?:can|could|may|am\s+i\s+allowed\s+to|is\s+it\s+(?:ok|okay|safe|fine))\b.{0,30}"
    r"\b(?:publish|present|post|share|submit|talk\s+about|release|put\s+(?:it\s+)?online|upload)\b.{0,50}"
    r"\b(?:before|without|prior\s+to|ahead\s+of)\b.{0,30}\b(?:patent\w*|fil(?:e|es|ing|ed)|disclos\w+|protect\w*)\b",
    re.I,
)
# How long the office's review takes. No loaded source says, so this is referred, never guessed.
_TIMELINE = [
    re.compile(r"\bhow\s+long\b.{0,40}\b(?:office|tto|review\w*|evaluat\w+|process\w*|approv\w+|hear\s+back)\b", re.I),
    re.compile(r"\bhow\s+(?:many\s+)?(?:days|weeks|months)\b.{0,40}\b(?:hear\s+back|until|before\s+(?:i|we)\s+(?:hear|get))\b", re.I),
    re.compile(r"\b(?:turnaround|response|review|processing)\s+time\b", re.I),
    re.compile(r"\bwhen\s+(?:will|would)\s+(?:the\s+)?(?:office|tto|they)\b.{0,30}\b(?:respond|reply|review|decide|get\s+back)\b", re.I),
]
_READINESS = [
    re.compile(
        r"\b(?:ready|mature|developed|far\s+enough|early\s+stage|enough\s+(?:data|results|evidence))\b.{0,40}"
        r"\b(?:disclos\w+|commerciali\w+|translat\w+|licens\w+|startup)\b",
        re.I,
    ),
    re.compile(r"\b(?:when\s+(?:should|do)|should)\s+(?:i|we)\s+(?:disclose|contact|reach\s+out|talk\s+to)\b", re.I),
]
_COI_CUES = re.compile(r"\b(?:equity|stock|consult\w*|outside|startup|company|conflict|royalt\w+|board)\b", re.I)


def _any(patterns, text: str) -> bool:
    return any(p.search(text) for p in patterns)


def classify_intent(text: str) -> Decision:
    q = strip_filler(text)
    if not q or _GREETING.match(q):
        return Decision(Intent.OUT_OF_SCOPE)
    definitional = bool(_DEFINITIONAL.match(q)) or bool(MEANING_REQUEST.search(q))
    # "for me" and "tell me" are politeness, not a question about the user's own work.
    explaining = definitional and not _PERSONAL.search(_POLITE_ME.sub(" ", q))
    coi = bool(_COI_CUES.search(q))
    # A pure definition is not a verdict request, but anything asked after it still is checked.
    scan = _after_first_sentence(q) if explaining else q

    if scan:
        if _any(_VERDICT, scan):
            return Decision(Intent.VERDICT_SEEKING, related_terms=["novelty", "prior_art", "patentability"], coi=coi)
        if _any(_INVENTORSHIP, scan):
            return Decision(Intent.INVENTORSHIP, related_terms=["inventorship"], coi=coi)
    # Pressure and role-play are never a definition, wherever they sit in the question.
    if _any(_OVERRIDE, q) or (scan and (_any(_LEGAL, scan) or _TIMING.search(scan))):
        timing = bool(_TIMING.search(q))
        return Decision(Intent.LEGAL_JUDGMENT, related_terms=["public_disclosure"] if timing else [], timing=timing, coi=coi)
    if _any(_TIMELINE, q):
        return Decision(Intent.PROCESS_TIMELINE, related_terms=["invention_disclosure"], coi=coi)
    if scan and _any(_READINESS, scan):
        return Decision(Intent.READINESS, related_terms=["translational_readiness", "development_stage"], coi=coi)
    if definitional:
        return Decision(Intent.CONCEPT, coi=coi)
    return Decision(Intent.POLICY, coi=coi)


def _contact_line(coi: bool) -> str:
    otc = _catalogue()["returns_to"]
    line = f"Contact the {otc}."  # the catalogue string already begins with the office's name
    if coi:
        line += f" For outside interests and conflicts: {COI_CONTACT}."
    return line


_BRING = (
    "What to bring: the draft disclosure, the dates of anything already public (papers, talks, posters, "
    "preprints) or planned, the funding sources with award numbers, and the names of everyone who "
    "contributed ideas."
)


def referral_block(decision: Decision) -> Block:
    """A kind, specific redirect: who can help, why, and what to bring."""
    kind = decision.intent
    if kind is Intent.VERDICT_SEEKING:
        title = "That is a call for the technology office, and here is how to get ready for it"
        why = (
            "Whether work is patentable, novel or commercially valuable is a judgment for the technology "
            "office and patent counsel. It depends on what is already public and on legal tests this tool "
            "does not apply, so it will not guess."
        )
        help_ = (
            "You can prepare now: write down what your work does differently from the closest existing "
            "approach, who would use it, and what evidence you have."
        )
        chips = ["What is prior art?", "What is novelty?", "What is differentiation?"]
    elif kind is Intent.INVENTORSHIP:
        title = "Who counts as an inventor is decided with patent counsel"
        why = (
            "Inventorship is a legal determination. It is not the same as who is an author on a paper, "
            "and this tool does not decide it."
        )
        help_ = "List everyone who contributed ideas to the invention and bring that list to the office."
        chips = ["What is inventorship?", "What is an invention disclosure?"]
    elif kind is Intent.PROCESS_TIMELINE:
        title = "I do not have the office's review times"
        why = (
            "None of the policies loaded here say how long the technology office's review takes, so this tool "
            "will not guess a number. It can depend on the case."
        )
        help_ = (
            "Ask the office when you submit, and say if a publication or talk is coming up, because that can "
            "affect how soon you need an answer."
        )
        chips = ["What is an invention disclosure?", "What is public disclosure?"]
    else:
        title = "That needs the technology office or counsel, not this tool"
        why = "This tool explains concepts and quotes policy. It does not give legal advice or tell you what to file, sign or publish."
        help_ = "Ask the office, and bring your questions with the details below."
        chips = ["What is public disclosure?", "What is an invention disclosure?"]
    if decision.timing:
        help_ += (
            " If a publication, talk or poster is coming up, contact the office before it happens, because "
            "public disclosure can limit patent rights."
        )
    body = "\n\n".join([why, help_, _BRING, _contact_line(decision.coi)])
    return Block(type="referral", source_label=SOURCE_REFERRAL, title=title, body=body, next_questions=chips)


def early_contact_block(decision: Decision) -> Block:
    """For readiness questions: disclosing early is encouraged, so do not make people wait."""
    body = "\n\n".join(
        [
            "You do not need to wait until the work feels finished. If a publication or talk is coming up, "
            "contact the office before it happens. Early conversations are how the office can help you "
            "decide what to protect and how.",
            _BRING,
            _contact_line(decision.coi),
        ]
    )
    return Block(
        type="referral",
        source_label=SOURCE_REFERRAL,
        title="Talk to the office early",
        body=body,
        next_questions=["What is public disclosure?", "What is an invention disclosure?"],
    )


def about_block() -> Block:
    return Block(
        type="referral",
        source_label=SOURCE_ABOUT,
        title="What I can help with",
        body=(
            "I can explain terms such as novelty, prior art, inventorship and public disclosure, quote the "
            "University of Missouri and UMKC policies we have loaded, and help you see what a disclosure "
            "does not yet say. I do not judge patentability or novelty, decide who is an inventor, or give "
            "legal advice."
        ),
        next_questions=["What is an invention disclosure?", "Who owns an invention I make using university resources?"],
    )
