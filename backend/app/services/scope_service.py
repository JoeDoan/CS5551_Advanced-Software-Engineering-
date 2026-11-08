import re
from typing import Any, Dict, List

from app.services import glossary_service

FORBIDDEN_PHRASES = (
    "is patentable",
    "is novel",
    "you should file",
    "you are an inventor",
    "you are not an inventor",
)

REFERRAL_SOURCE_LABEL = (
    "Referral: needs the technology office or the conflict of interest office"
)

_VERDICT_PATTERNS = (
    r"\bpatentable\b",
    r"\bis\s+(?:this|my|our|the|it)\b[^?]*\bnovel\b",
    r"\bnovel\s+enough\b",
    r"\bshould\s+(?:i|we|our\s+lab|our\s+team)\s+file\b",
    r"\bwhether\s+to\s+file\s+a?\s*(?:provisional|patent|application)\b",
    r"\bworth\s+(?:filing|patenting)\b",
    r"\bcan\s+(?:i|we)\s+patent\s+(?:this|my|our)\b",
    r"\bwill\s+(?:this|my|our|the\s+office)\b[^?]*\bget\s+a\s+patent\b",
    r"\bchance(?:s)?\s+of\s+getting\s+a\s+patent\b",
    r"\bpass(?:es)?\s+(?:the\s+)?(?:novelty|non-?obviousness|section\s+10[123])\b",
    r"\bobvious\s+over\b",
    r"\banticipate(?:d|s)?\s+by\b",
    r"\bfreedom\s+to\s+operate\b",
    r"\binfringe(?:s|d|ment)?\b",
    r"\bhow\s+many\s+(?:days|weeks|months|business\s+days)\b[^?]*\b(?:technology\s+office|tto|ori|file|patent|provisional|review|take)\b",
    r"\bhow\s+long\s+(?:will|does)\s+the\s+(?:technology\s+office|tto|university)\s+take\s+to\s+file\b",
    r"\bguaranteed?\s+turnaround\s+time\b",
    r"\bsla\s+(?:for|to)\s+fil(?:e|ing)\b",
    r"\bjust\s+say\s+yes\s+or\s+no\b",
    r"\byes\s+or\s+no\s*:\s*is\b",
)

_INVENTORSHIP_PATTERNS = (
    r"\b(?:am\s+i|is\s+my|is\s+our|is\s+the|is\s+a|is\s+he|is\s+she|are\s+we|are\s+they)\b[^?]*\b(?:legally\s+)?(?:an?\s+)?(?:co-?)?inventor(?:s)?\b",
    r"\bwho\s+(?:is|counts\s+as|qualifies\s+as)\s+(?:legally\s+)?(?:an?\s+)?(?:co-?)?inventor\b",
    r"\bcount(?:s)?\s+as\s+(?:an?\s+)?(?:co-?)?inventor\b",
    r"\bqualif(?:y|ies)\s+as\s+(?:an?\s+)?(?:co-?)?inventor\b",
    r"\b(?:add|remove|drop|exclude|leave\s+off|put|list|listed|name|named|include|included)\b[^?]*\b(?:as\s+)?(?:an?\s+)?(?:co-?)?inventor\b",
    r"\bshould\s+(?:my|the|a|our)\b[^?]*\b(?:co-?)?inventor\b",
    r"\bco-?inventor\s+on\s+claim\b",
    r"\bdeserve(?:s)?\s+to\s+be\s+(?:an?\s+)?(?:co-?)?inventor\b",
    r"\binventorship\s+dispute\b",
)

_LEGAL_JUDGMENT_PATTERNS = (
    r"\b(?:section|clause|article|paragraph)\s+\d+[a-z]?\s+of\s+(?:our|my|the)\b",
    r"\b(?:sponsor|sponsored\s+research|industry|company|corporate)\s+(?:contract|agreement)\s+(?:give|grant|allow|require|mean|entitle)\b",
    r"\bautomatic\s+(?:exclusive|non-?exclusive|royalty-?free)\s+licen[cs]e\b",
    r"\bindemnif(?:y|ication)\b",
    r"\bbreach\s+of\s+contract\b",
    r"\b(?:nda|mta|cda|material\s+transfer\s+agreement|contract|agreement|clause)\b[^?]*\b(?:legally\s+)?(?:enforceable|binding|valid|void)\b",
    r"\binterpret\s+(?:section|clause|our\s+contract|this\s+agreement)\b",
    r"\blegal\s+opinion\s+on\b",
    r"\blegally\s+entitle(?:d)?\s+under\s+(?:our|the)\s+(?:contract|agreement)\b",
)

_OFF_TOPIC_PATTERNS = (
    r"\b(?:parking|permit\s+fee|campus\s+parking|meter|garage)\b",
    r"\b(?:pizza|restaurant|coffee|cafeteria|dining\s+hall|catering)\b",
    r"\b(?:gym|recreation\s+center|basketball|soccer\s+tickets|athletics)\b",
    r"\b(?:dorm|housing\s+fee|meal\s+plan|tuition\s+rate|bookstore)\b",
    r"\b(?:weather|forecast\s+today|traffic\s+on)\b",
    r"\bzzqx\b",
)

_IN_SCOPE_POLICY_CUES = re.compile(
    r"\b(?:"
    r"invention|inventions|inventor|inventors|patent|patents|copyright|copyrights|"
    r"trademark|trademarks|trade\s+secret|trade\s+secrets|bayh-?dole|royalt(?:y|ies)|"
    r"proceeds|licen[cs](?:e|es|ing)|ownership|owns|own|assign|assignment|waive|waiver|"
    r"reassign|disclosure|disclose|conflict\s+of\s+interest|conflicts\s+of\s+interest|"
    r"fcoi|financial\s+interest|outside\s+interest|outside\s+activity|outside\s+company|"
    r"consulting|startup|spinout|equity|stock|sanction|sanctions|training|investigator|"
    r"investigators|scholarly|syllabus|lecture\s+notes|books|articles|courseware|"
    r"equipment|facilities|resources|substantial\s+use|patent\s+committee|federal\s+grant|"
    r"federally\s+funded|sponsored|phd\s+student|enrolled\s+students"
    r")\b",
    re.I,
)


def claims_filter(text: str) -> bool:
    lowered = text.lower()
    return not any(phrase in lowered for phrase in FORBIDDEN_PHRASES)


def classify_intent(question: str) -> str:
    cleaned = question.strip()
    lowered = cleaned.lower()

    if not cleaned:
        return "out_of_scope"

    if any(re.search(pat, lowered, re.I) for pat in _OFF_TOPIC_PATTERNS):
        return "out_of_scope"

    if any(re.search(pat, lowered, re.I) for pat in _LEGAL_JUDGMENT_PATTERNS):
        return "legal_judgment"

    if not re.search(r"how\s+is\s+inventorship\s+different\s+from\s+authorship", lowered, re.I):
        if any(re.search(pat, lowered, re.I) for pat in _INVENTORSHIP_PATTERNS):
            return "inventorship"

    if any(re.search(pat, lowered, re.I) for pat in _VERDICT_PATTERNS):
        return "verdict_seeking"

    if glossary_service.lookup(cleaned) is not None:
        return "concept"

    if _IN_SCOPE_POLICY_CUES.search(lowered):
        return "policy"

    return "out_of_scope"


def build_referral_block(intent: str, question: str) -> Dict[str, Any]:
    if intent == "inventorship":
        title = "Inventorship determination requires technology office review"
        body = (
            "Determining who qualifies as a legal inventor on specific patent claims requires a "
            "claim-by-claim review by the UMKC Office of Research Services / Technology "
            "Commercialization (umkcor@umkc.edu) and patent counsel, and any related outside "
            "roles can be reviewed with the UMKC Conflict of Interest Office (umkccoi@umkc.edu). "
            "Bring your UM-16C draft, a summary of each contributor's technical role, and any "
            "funding or student appointment details."
        )
        next_questions: List[str] = [
            "How is inventorship different from authorship on a paper?",
            "What are the conditions for enrolled students to assign inventions to the university?",
        ]
    elif intent == "legal_judgment":
        title = "Contract and licensing interpretation requires campus review"
        body = (
            "Interpreting specific clauses in a sponsored research agreement, material transfer "
            "agreement, or license requires review by the UMKC Office of Research Services / "
            "Technology Commercialization (umkcor@umkc.edu) and the UMKC Conflict of Interest "
            "Office (umkccoi@umkc.edu). Bring the full signed or proposed agreement, the sponsor "
            "name, and your UM-16C invention disclosure draft."
        )
        next_questions = [
            "What does licence mean?",
            "Who owns an invention I make using university resources?",
        ]
    elif intent == "verdict_seeking":
        title = "Patentability, filing decisions, and timelines require office review"
        body = (
            "Assessing patentability over prior references, deciding filing timing, or estimating "
            "office evaluation schedules requires review by the UMKC Office of Research Services / "
            "Technology Commercialization (umkcor@umkc.edu) and, when outside interests exist, "
            "the UMKC Conflict of Interest Office (umkccoi@umkc.edu). Bring your UM-16C draft, "
            "closest known references, and any upcoming publication or conference dates."
        )
        next_questions = [
            "What does novelty mean in an invention disclosure?",
            "What counts as a public disclosure before filing a patent?",
        ]
    else:
        title = "Outside loaded policy passages"
        body = (
            "This question is outside the loaded University of Missouri and UMKC commercialization "
            "and conflict-of-interest policies. For commercialization or invention questions, "
            "contact the UMKC Office of Research Services / Technology Commercialization "
            "(umkcor@umkc.edu); for outside-activity or conflict questions, contact the UMKC "
            "Conflict of Interest Office (umkccoi@umkc.edu)."
        )
        next_questions = [
            "Who owns an invention I make using university resources?",
            "What is a conflict of interest?",
        ]

    return {
        "type": "referral",
        "source_label": REFERRAL_SOURCE_LABEL,
        "title": title,
        "body": body,
        "citations": [],
        "next_questions": next_questions,
    }
