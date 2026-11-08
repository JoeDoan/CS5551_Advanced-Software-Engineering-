import json
from datetime import date

import pytest

import app.services.idf_service as idf
from app.services import copilot_service as copilot
from app.services.policy_service import CORPUS_PATH, answer_question

BASE = "/api/v1/commercialization"

MANUSCRIPT = """Low-cost Acoustic Sensing of Bridge Cracks
Jane Q. Researcher, Alan B. Colleague
Abstract: We propose a passive acoustic method that locates hairline cracks in steel bridges using inexpensive microphones. The method needs no traffic closure. It reaches the accuracy of ultrasonic scanning in field trials. A prototype ran for six months on two bridges.
Keywords: acoustic sensing; structural health monitoring; bridges
1. Introduction
The main challenge in bridge inspection is that ultrasonic scanning is slow and requires lane closures. Unlike existing methods, our approach runs continuously and unattended.
Results were published online March 3, 2025 in a workshop proceeding and presented at the summer meeting.
A limitation is that the method does not work on concrete decks without further calibration.
Acknowledgments
This work was supported by the National Science Foundation under grant number 2012345 and by a seed grant from the university.
References
[1] Smith, P. Ultrasonic inspection of welded joints. Journal of Testing 12, 2019.
[2] Lee, K. Acoustic emission monitoring of steel bridges. Structures 8, 2021.
"""


def _pdf(text: str) -> bytes:
    """A tiny one-page PDF whose text pypdf can read."""
    lines = [ln.replace("(", "[").replace(")", "]") for ln in text.splitlines() if ln.strip()]
    stream = "BT /F1 9 Tf 40 760 Td 11 TL " + " ".join(f"({ln[:110]}) Tj T*" for ln in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


# ----------------------------------------------------------------- policy guardrail
def test_policy_answers_cite_real_passages_verbatim():
    corpus = {p["id"]: p for p in json.load(open(CORPUS_PATH, encoding="utf-8"))["passages"]}
    ans = answer_question("Can my PhD student write code for my startup?")
    assert ans.answered and ans.citations
    for c in ans.citations:
        assert c.text == corpus[c.passage_id]["text"]  # never paraphrased
        assert c.source_url.startswith("https://") and c.version
    assert any(c.source_title.startswith("UM Collected Rules 100") for c in ans.citations)
    assert "not legal advice" in ans.disclaimer


def test_policy_refuses_off_topic_and_unanswerable_questions():
    assert not answer_question("What is the best pizza in Kansas City?").answered
    assert not answer_question("What is the parking policy at Volker campus?").answered
    none = answer_question("zzqx wibble outside")
    assert not none.answered and "does not mean it is allowed" in none.message


def test_policy_route_and_validation(client):
    ok = client.post(f"{BASE}/policy/ask", json={"question": "Who owns my invention?"})
    assert ok.status_code == 200 and ok.json()["answered"] is True
    assert client.post(f"{BASE}/policy/ask", json={"question": "x"}).status_code == 422
    assert client.post(f"{BASE}/policy/ask", json={"question": "a" * 601}).status_code == 422


# --------------------------------------------------------------------- IDF drafter
def _by_id(resp):
    return {f["id"]: f for f in resp["fields"]}


def test_draft_proposes_narrative_fields_with_evidence_and_leaves_human_fields_blank(client):
    r = client.post(f"{BASE}/idf/draft-text", json={"text": MANUSCRIPT})
    assert r.status_code == 200, r.text
    body = r.json()
    fields = _by_id(body)
    assert len(fields) == 26 and sum(body["counts"].values()) == 26
    assert body["extractor"] == "rules" and body["llm_status"] == "disabled"
    assert fields["A1_title"]["value"].startswith("Low-cost Acoustic Sensing")
    assert fields["A1_general"]["status"] == "proposed"
    assert fields["A1_keywords"]["value"].startswith("acoustic sensing")
    for f in body["fields"]:
        if f["fill"] == "human":
            assert f["status"] == "blank" and f["value"] == ""
        if f["value"]:
            assert idf.quote_is_grounded(f["evidence"], MANUSCRIPT), f["id"]
    # confirm-me fields are marked as needing the author, never silently "proposed"
    assert fields["B1_types"]["status"] == "needs_author"
    assert fields["C1_inventors"]["status"] in ("needs_author", "blank")
    assert fields["E_submitter"]["status"] == "blank"


def test_public_disclosure_date_drives_the_patent_window_flag():
    values = idf.draft_with_rules(MANUSCRIPT)
    assert values["A2_first_public"]["value"] == "March 3, 2025"
    ended = idf.build_flags(values, today=date(2026, 11, 1))
    assert any("appears to have ended on 2026-03-03" in f.message for f in ended)
    open_window = idf.build_flags(values, today=date(2025, 6, 1))
    assert any("2026-03-03" in f.message and "ended" not in f.message for f in open_window)
    assert any("Federal funding" in f.message for f in ended)


def test_pdf_upload_round_trip(client):
    r = client.post(
        f"{BASE}/idf/draft", files={"file": ("paper.pdf", _pdf(MANUSCRIPT), "application/pdf")}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages_read"] == 1
    assert _by_id(body)["A1_title"]["value"].startswith("Low-cost Acoustic Sensing")


def test_bad_uploads_are_rejected_clearly(client):
    notpdf = client.post(f"{BASE}/idf/draft", files={"file": ("a.pdf", b"hello", "application/pdf")})
    assert notpdf.status_code == 422 and "not a PDF" in notpdf.json()["detail"]
    scanned = client.post(
        f"{BASE}/idf/draft", files={"file": ("s.pdf", _pdf("tiny"), "application/pdf")}
    )
    assert scanned.status_code == 422 and "Not enough readable text" in scanned.json()["detail"]


def test_claude_values_without_a_matching_quote_are_dropped(monkeypatch):
    item = idf._Item
    fake = idf.LLMDraft(
        title=item(value="Acoustic bridge crack sensing", evidence="Low-cost Acoustic Sensing of Bridge Cracks"),
        general=item(value="A made-up claim", evidence="we achieve ten times the accuracy of any method"),
        technical=None, novel=None, problem=None, different=None, limits=None,
        competition=None, keywords=None, first_public_disclosure=None,
        funders=[item(value="NSF grant 2012345", evidence="National Science Foundation under grant number 2012345")],
        prior_art=[], authors=[],
    )
    monkeypatch.setattr(copilot, "llm_enabled", lambda: True)
    monkeypatch.setattr(idf, "_call_llm", lambda text: fake)
    resp = idf.draft_idf(MANUSCRIPT, use_llm=True)
    fields = {f.id: f for f in resp.fields}
    assert resp.extractor == "claude" and fields["A1_title"].status == "proposed"
    assert fields["A1_general"].status == "blank"  # fabricated quote -> dropped
    assert any("A1_general" in w and "not found" in w for w in resp.warnings)
    assert fields["B1_details"].value == "NSF grant 2012345"


def test_claude_failure_falls_back_to_the_offline_extractor(monkeypatch):
    def down(_text):
        raise copilot.LLMError("could not reach the API")

    monkeypatch.setattr(copilot, "llm_enabled", lambda: True)
    monkeypatch.setattr(idf, "_call_llm", down)
    resp = idf.draft_idf(MANUSCRIPT, use_llm=True)
    assert resp.extractor == "rules" and resp.llm_status == "failed"
    assert any("offline extractor" in w for w in resp.warnings)


def test_llm_is_never_used_unless_requested(monkeypatch):
    monkeypatch.setattr(copilot, "llm_enabled", lambda: True)
    monkeypatch.setattr(idf, "_call_llm", lambda t: pytest.fail("document was sent to Claude"))
    assert idf.draft_idf(MANUSCRIPT).extractor == "rules"


def test_requires_login_when_auth_is_on(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post(f"{BASE}/policy/ask", json={"question": "Who owns my invention?"}).status_code == 401
    assert client.post(f"{BASE}/idf/draft-text", json={"text": MANUSCRIPT}).status_code == 401
    assert client.get(f"{BASE}/status").status_code == 401


# ------------------------------------------------------------------ industry matcher
def test_matcher_maps_the_manuscript_to_infrastructure_and_sensing(client):
    r = client.post(f"{BASE}/match", json={"text": MANUSCRIPT})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched"] is True
    ids = [m["id"] for m in body["matches"]]
    assert ids[0] == "infrastructure-monitoring" and "industrial-sensing" in ids
    top = body["matches"][0]
    assert {"bridge", "crack"} <= set(top["matched_terms"])  # shows why it matched
    assert all(len(n["code"]) == 6 and n["code"].isdigit() for n in top["naics"])
    assert "not market research" in body["note"]


def test_matcher_says_so_when_nothing_fits():
    from app.services.matcher_service import match_industries

    out = match_industries("A study of medieval poetry and the history of lyric forms in Europe.")
    assert out.matched is False and out.matches == []
    assert "No industry" in out.message


def test_matcher_naics_codes_are_unique_six_digit_strings():
    import json as _json

    from app.services.matcher_service import MAP_PATH

    for ind in _json.load(open(MAP_PATH, encoding="utf-8"))["industries"]:
        codes = [n["code"] for n in ind["naics"]]
        assert len(codes) == len(set(codes))
        assert all(c.isdigit() and len(c) == 6 for c in codes)
        assert ind["sbir_agencies"] and ind["pain_points"]


def test_matcher_validation(client):
    assert client.post(f"{BASE}/match", json={"text": "short"}).status_code == 422


# ------------------------------------------------------------- the shipped sample paper
SAMPLE_PDF = str(
    idf.Path(__file__).resolve().parents[2]
    / "docs"
    / "samples"
    / "sample_paper_bridge_cracks.pdf"
)


def test_sample_paper_drafts_cleanly_and_every_value_is_a_true_excerpt():
    text, pages = idf.extract_pdf_text(open(SAMPLE_PDF, "rb").read())
    resp = idf.draft_idf(text, pages)
    fields = {f.id: f for f in resp.fields}
    for f in resp.fields:
        if f.value:
            assert idf.quote_is_grounded(f.evidence, text), f.id
    # headings, bylines and the keyword line never leak into sentence fields
    for fid in ("A1_general", "A1_novel", "A1_problem", "A1_different", "A1_limits"):
        v = fields[fid].value
        assert v and not any(w in v for w in ("Introduction", "Keywords:", "Colleague", "Limitations "))
    assert fields["A1_problem"].value != fields["A1_different"].value
    assert fields["A2_first_public"].value == "June 12, 2026"
    assert fields["B1_types"].value == "Federal"
    assert any(f.level == "deadline" for f in resp.flags)
