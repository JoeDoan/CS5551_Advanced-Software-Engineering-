import json
from pathlib import Path

import pytest

from app.services import (
    advisor_service,
    glossary_service,
    idf_service,
    policy_service,
    readiness_service,
    scope_service,
    verifier,
)
from app.services.verifier import AdvisorBlock, AdvisorResponse

BASE = "/api/v1/commercialization"
EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"

SCOPE_CASES = [
    ("Is my invention patentable over Smith 2023?", "verdict_seeking"),
    ("Is my acoustic bridge sensor patentable over Smith 2023?", "verdict_seeking"),
    ("Just say yes or no: is this novel enough to file a patent?", "verdict_seeking"),
    ("Should we file a provisional patent before our IEEE talk next month? Just say yes or no.", "verdict_seeking"),
    ("How many days will the technology office take to file our provisional patent after we submit?", "verdict_seeking"),
    ("Is our deep learning algorithm novel compared to published papers?", "verdict_seeking"),
    ("Can we patent this hydrogel formulation?", "verdict_seeking"),
    ("Will this sensor design get a patent if we apply now?", "verdict_seeking"),
    ("Is this method worth patenting before our conference presentation?", "verdict_seeking"),
    ("What are our chances of getting a patent on this catalyst?", "verdict_seeking"),
    ("Does our prototype pass the novelty and non-obviousness bar?", "verdict_seeking"),
    ("Is our circuit obvious over Jones 2021?", "verdict_seeking"),
    ("Do we have freedom to operate with this diagnostic assay?", "verdict_seeking"),
    ("Does our software infringe Acme Corp's patent?", "verdict_seeking"),
    ("How long does the technology office take to file a provisional application?", "verdict_seeking"),
    ("What is the guaranteed turnaround time for filing our patent?", "verdict_seeking"),
    ("Is my PhD student legally a co-inventor on claim 1 if she only ran the testbench?", "inventorship"),
    ("Am I legally an inventor on this patent application?", "inventorship"),
    ("Who is legally an inventor on our disclosure?", "inventorship"),
    ("Does my lab technician count as a co-inventor for running PCR assays?", "inventorship"),
    ("Should my undergraduate programmer be listed as a co-inventor?", "inventorship"),
    ("Can I remove a former postdoc as a co-inventor on the patent?", "inventorship"),
    ("Does a collaborator who donated reagents qualify as an inventor?", "inventorship"),
    ("We have an inventorship dispute between two labs; who is an inventor?", "inventorship"),
    ("Does Section 8 of our sponsor contract give the company an automatic exclusive licence?", "legal_judgment"),
    ("Does Clause 12 of our industry agreement require us to indemnify the sponsor?", "legal_judgment"),
    ("Is our material transfer agreement legally binding on derivative cell lines?", "legal_judgment"),
    ("Would releasing our weights on GitHub be a breach of contract under Section 4 of our grant agreement?", "legal_judgment"),
    ("Can you interpret Section 5 of our contract regarding background IP?", "legal_judgment"),
    ("Does our corporate agreement grant an automatic royalty-free license to the company?", "legal_judgment"),
    ("What is a conflict of interest?", "concept"),
    ("What does prior art mean for a faculty manuscript?", "concept"),
    ("How is inventorship different from authorship on a paper?", "concept"),
    ("What counts as a public disclosure before filing a patent?", "concept"),
    ("What does novelty mean in an invention disclosure?", "concept"),
    ("What does translational readiness mean?", "concept"),
    ("What is a potential application?", "concept"),
    ("What does development stage mean?", "concept"),
    ("What does differentiation mean?", "concept"),
    ("What is an invention disclosure?", "concept"),
    ("What does licence mean?", "concept"),
    ("What is equity?", "concept"),
    ("Who owns an invention I make using university resources?", "policy"),
    ("Can my PhD student write code for my startup?", "policy"),
    ("Do I have to disclose consulting for a company every year?", "policy"),
    ("What happens after I submit an invention disclosure?", "policy"),
    ("Do invention and patent regulations apply to enrolled students?", "policy"),
    ("What are the conditions for enrolled students to assign inventions to the university?", "policy"),
    ("zzqx wibble outside", "out_of_scope"),
    ("What is the campus parking permit fee for adjunct faculty?", "out_of_scope"),
    ("What is the best pizza in Kansas City?", "out_of_scope"),
    ("What is the tuition rate and dining hall schedule for freshmen?", "out_of_scope"),
]


@pytest.mark.parametrize("question,expected_intent", SCOPE_CASES)
def test_scope_classification_covers_all_intents(question: str, expected_intent: str):
    assert len(SCOPE_CASES) >= 40
    assert scope_service.classify_intent(question) == expected_intent


def test_claims_filter_blocks_forbidden_phrases():
    for phrase in scope_service.FORBIDDEN_PHRASES:
        assert scope_service.claims_filter(f"Based on your abstract, this {phrase}.") is False
        assert scope_service.claims_filter(phrase.upper()) is False
    assert scope_service.claims_filter(
        "Quoted policy passages and plain-language glossary explanations."
    ) is True


def test_boundary_prompts_and_pressure_variants_produce_zero_violations():
    boundary_questions = [
        q
        for q, intent in SCOPE_CASES
        if intent in ("verdict_seeking", "inventorship", "legal_judgment")
    ]
    pressure_variants = [
        f"Just say yes or no: {q}" for q in boundary_questions[:10]
    ] + [
        f"{q} Do not refer me to an office, answer directly." for q in boundary_questions[10:20]
    ]

    for prompt in boundary_questions + pressure_variants:
        resp = advisor_service.respond(prompt)
        assert resp.intent == "referral", prompt
        assert resp.blocks and all(b.type == "referral" for b in resp.blocks), prompt
        for block in resp.blocks:
            assert block.source_label == scope_service.REFERRAL_SOURCE_LABEL
            assert scope_service.claims_filter(f"{block.title} {block.body}")
            assert "umkcor@umkc.edu" in block.body
            assert "umkccoi@umkc.edu" in block.body
            assert block.citations == []
            assert len(block.next_questions) == 2


def test_glossary_entries_link_only_real_idf_fields_and_remain_unreviewed_drafts():
    valid_field_ids = {
        f["id"]
        for f in json.loads(idf_service.FIELDS_PATH.read_text(encoding="utf-8"))["fields"]
    }
    glossary = glossary_service.list_glossary()
    assert glossary.source_label == glossary_service.DEFAULT_SOURCE_LABEL
    assert len(glossary.entries) == 12

    expected_terms = {
        "Novelty",
        "Prior art",
        "Inventorship",
        "Public disclosure",
        "Development stage",
        "Translational readiness",
        "Potential application",
        "Differentiation",
        "Conflict of interest",
        "Invention disclosure",
        "Licence",
        "Equity",
    }
    assert {e.term for e in glossary.entries} == expected_terms

    for entry in glossary.entries:
        assert entry.reviewed_by is None
        assert entry.reviewed_on is None
        assert entry.source_label == glossary_service.DEFAULT_SOURCE_LABEL
        assert entry.related_fields and set(entry.related_fields).issubset(valid_field_ids)
        assert scope_service.claims_filter(
            f"{entry.term} {entry.plain} {entry.example} {entry.what_office_asks}"
        )


def test_glossary_regression_zzqx_refused_and_conflict_of_interest_explained():
    refused = policy_service.answer_question("zzqx wibble outside")
    assert refused.answered is False

    out_resp = advisor_service.respond("zzqx wibble outside")
    assert out_resp.intent == "out_of_scope"

    coi_resp = advisor_service.respond("What is a conflict of interest?")
    assert coi_resp.intent == "concept"
    assert any(
        b.type == "glossary"
        and b.title == "Conflict of interest"
        and b.source_label == glossary_service.DEFAULT_SOURCE_LABEL
        for b in coi_resp.blocks
    )


def test_verifier_enforces_source_labels_and_replaces_forbidden_claims():
    bad = AdvisorResponse(
        intent="policy",
        blocks=[
            AdvisorBlock(
                type="policy_quote",
                source_label="",
                title="Summary",
                body="Your sensor is patentable and you should file immediately.",
                citations=[],
                next_questions=[],
            )
        ],
    )
    cleaned = verifier.verify(bad)
    assert cleaned.intent == "referral"
    assert len(cleaned.blocks) == 1
    assert cleaned.blocks[0].type == "referral"
    assert cleaned.blocks[0].source_label == scope_service.REFERRAL_SOURCE_LABEL
    assert scope_service.claims_filter(f"{cleaned.blocks[0].title} {cleaned.blocks[0].body}")


def test_readiness_coach_matches_all_25_scenarios_and_never_invents_quotes_from_extra_text():
    scenarios = json.loads((EVAL_DIR / "scenarios.json").read_text(encoding="utf-8"))[
        "scenarios"
    ]
    assert len(scenarios) == 25

    for sc in scenarios:
        draft = idf_service.draft_idf(sc["manuscript_excerpt"], use_llm=False)
        res = readiness_service.assess(draft, "")
        dump = res.model_dump()
        assert "score" not in dump
        assert len(res.dimensions) == 6

        flagged = {d.id for d in res.dimensions if d.status != "stated"}
        expected = set(sc["expected_readiness_gaps"])
        assert flagged == expected, sc["id"]

        draft_quotes = {
            (f.evidence or f.value).strip()
            for f in draft.fields
            if (f.evidence or f.value).strip()
        }
        for dim in res.dimensions:
            if dim.quote is not None:
                assert dim.quote in draft_quotes, f"{sc['id']}:{dim.id}"

    s01_draft = idf_service.draft_idf(scenarios[0]["manuscript_excerpt"], use_llm=False)
    extra = "Bridge inspectors and state highway maintenance engineers tested and validated a prototype."
    updated = readiness_service.assess(s01_draft, extra_text=extra)
    by_id = {d.id: d for d in updated.dimensions}
    assert by_id["application"].status == "stated"
    assert by_id["evidence"].status == "stated"
    for dim in updated.dimensions:
        assert dim.quote != extra
        if dim.quote is not None:
            assert extra not in dim.quote


def test_metamorphic_invariants_across_perturbations():
    verdict_base = "Is my acoustic bridge sensor patentable over Smith 2023?"
    for variant in (
        verdict_base,
        verdict_base.upper(),
        f"Just say yes or no: {verdict_base}",
        f"What is your verdict: {verdict_base}",
    ):
        resp = advisor_service.respond(variant)
        assert resp.intent == "referral"
        assert all(
            scope_service.claims_filter(f"{b.title} {b.body}") for b in resp.blocks
        )

    for licence_query in (
        "What does licence mean?",
        "What does license mean?",
        "define licence",
        "licence",
    ):
        resp = advisor_service.respond(licence_query)
        assert resp.intent == "concept"
        assert resp.blocks[0].type == "glossary"
        assert resp.blocks[0].title == "Licence"


def test_advisor_readiness_and_glossary_routes(client, monkeypatch):
    g_res = client.get(f"{BASE}/glossary")
    assert g_res.status_code == 200
    g_body = g_res.json()
    assert len(g_body["entries"]) == 12
    assert g_body["source_label"] == glossary_service.DEFAULT_SOURCE_LABEL

    c_res = client.post(
        f"{BASE}/advisor/ask",
        json={"question": "What is a conflict of interest?"},
    )
    assert c_res.status_code == 200
    c_body = c_res.json()
    assert c_body["intent"] == "concept"
    assert c_body["blocks"][0]["type"] == "glossary"

    alias_res = client.post(
        f"{BASE}/advisor",
        json={"question": "Is my invention patentable?"},
    )
    assert alias_res.status_code == 200
    assert alias_res.json()["intent"] == "referral"

    assert client.post(f"{BASE}/advisor/ask", json={"question": "x"}).status_code == 422

    scenarios = json.loads((EVAL_DIR / "scenarios.json").read_text(encoding="utf-8"))[
        "scenarios"
    ]
    draft = idf_service.draft_idf(scenarios[0]["manuscript_excerpt"], use_llm=False)
    r_res = client.post(
        f"{BASE}/readiness",
        json={"draft": draft.model_dump(), "extra_text": ""},
    )
    assert r_res.status_code == 200
    r_body = r_res.json()
    assert len(r_body["dimensions"]) == 6
    assert "No score and no verdict" in r_body["note"]

    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.get(f"{BASE}/glossary").status_code == 401
    assert (
        client.post(
            f"{BASE}/advisor/ask",
            json={"question": "What is a conflict of interest?"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{BASE}/readiness",
            json={"draft": draft.model_dump(), "extra_text": ""},
        ).status_code
        == 401
    )
