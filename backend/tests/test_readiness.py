import pytest

import app.services.idf_service as idf
from app.services import readiness_service as r
from app.services.verifier import claims_filter
from tests.test_commercialization import BASE, MANUSCRIPT

READY = f"{BASE}/readiness"
PAD = " ".join(["The notation used throughout is defined in the appendix."] * 8)
THIN = "A Graph Ranking Method\nAbstract: We propose a new algorithm for ranking documents using graph structure.\n" + PAD
IDS = ["problem", "application", "difference", "evidence", "related_work", "timing"]


def _by_id(result):
    return {d.id: d for d in result.dimensions}


def test_result_has_the_six_dimensions_in_a_fixed_order_and_no_score():
    res = r.assess(idf.draft_idf(text=MANUSCRIPT))
    assert [d.id for d in res.dimensions] == IDS
    assert set(res.model_json_schema()["properties"]) == {"dimensions", "note"}  # frozen: no score field
    assert set(r.Dimension.model_json_schema()["properties"]) == {"id", "status", "quote", "follow_up", "needs_author"}
    assert "No score and no verdict" in res.note


def test_a_full_draft_is_read_from_the_authors_own_words():
    d = _by_id(r.assess(idf.draft_idf(text=MANUSCRIPT)))
    assert d["problem"].status == "stated" and "bridge inspection" in d["problem"].quote
    assert d["difference"].status == "stated" and d["difference"].follow_up is None
    assert d["timing"].status == "stated" and "March 3, 2025" in d["timing"].quote
    assert d["timing"].needs_author  # a date found in a paper still needs the author to confirm it
    assert d["related_work"].status == "partly" and d["related_work"].needs_author  # present is not verified
    assert d["evidence"].status in ("partly", "stated") and d["evidence"].quote


def test_industry_match_alone_is_partly_never_stated_for_application():
    d = _by_id(r.assess(idf.draft_idf(text=MANUSCRIPT)))["application"]
    assert d.status == "partly" and d.quote is None and d.follow_up and d.needs_author


def test_a_thin_draft_gets_one_follow_up_per_gap_and_invents_nothing():
    res = r.assess(idf.draft_idf(text=THIN))
    for d in res.dimensions:
        assert d.status == "not_found" and d.quote is None and d.needs_author
        assert d.follow_up == r.FOLLOW_UPS[d.id]
    assert len({d.follow_up for d in res.dimensions}) == 6


def test_extra_text_fills_gaps_and_is_quoted_exactly():
    extra = "We tested it on two datasets and measured accuracy. Librarians would use it. We presented a poster at a workshop in May."
    d = _by_id(r.assess(idf.draft_idf(text=THIN), extra))
    assert d["evidence"].status == "stated" and d["evidence"].quote in extra
    assert d["application"].status == "stated" and d["application"].quote in extra
    assert d["timing"].status == "partly" and d["timing"].quote in extra
    assert d["problem"].status == "not_found"  # the extra text did not touch it


def test_every_quote_is_a_true_excerpt_of_the_draft_or_the_extra_text():
    extra = "Clinicians would use this. We measured it and tested it. A preprint is out."
    draft = idf.draft_idf(text=MANUSCRIPT)
    source = " ".join(" ".join([f.value, f.evidence]) for f in draft.fields) + " " + extra
    source = " ".join(source.split())
    for dim in r.assess(draft, extra).dimensions:
        if dim.quote:
            assert dim.quote in source, (dim.id, dim.quote)
            assert len(dim.quote) <= r.MAX_QUOTE_CHARS


def test_human_only_fields_are_never_read_as_evidence():
    draft = idf.draft_idf(text=THIN)
    for f in draft.fields:
        if f.id == "A2_prototype":
            f.value = "tested validated measured prototype results"  # even if someone fills it in
    assert _by_id(r.assess(draft))["evidence"].status == "not_found"


def test_one_cue_word_is_partly_two_different_cue_words_is_stated():
    one = _by_id(r.assess(idf.draft_idf(text=THIN), "We tested tested tested it."))["evidence"]
    two = _by_id(r.assess(idf.draft_idf(text=THIN), "We tested it and measured the error."))["evidence"]
    assert one.status == "partly" and two.status == "stated"


def test_marking_a_dimension_covered_elsewhere_removes_its_follow_up_but_not_its_status():
    res = _by_id(r.assess(idf.draft_idf(text=THIN), covered_elsewhere=["problem", "timing"]))
    for k in ("problem", "timing"):
        assert res[k].follow_up is None and not res[k].needs_author and res[k].status == "not_found"
    assert res["evidence"].follow_up  # the others are unchanged


def test_extra_text_is_capped():
    draft = idf.draft_idf(text=THIN)
    long = "We tested it. " * 500
    assert r.assess(draft, long).dimensions  # does not raise; only the first chars are used


def test_the_coach_never_issues_a_verdict_or_a_score():
    for text, extra in [(MANUSCRIPT, ""), (THIN, ""), (THIN, "tested measured clinicians would use it")]:
        res = r.assess(idf.draft_idf(text=text), extra)
        questions = " ".join(d.follow_up or "" for d in res.dimensions)
        assert claims_filter(res.note + " " + questions) == []
        assert not any(w in questions.lower() for w in ("score", "rating", "ready", "weak", "strong"))
        assert all(d.follow_up.endswith("?") for d in res.dimensions if d.follow_up)


@pytest.mark.parametrize("dim", IDS)
def test_follow_up_bank_covers_every_dimension(dim):
    assert r.FOLLOW_UPS[dim].endswith("?") and r.TITLES[dim]


def test_route_returns_the_contract_shape(client):
    draft = client.post(f"{BASE}/idf/draft-text", json={"text": MANUSCRIPT}).json()
    res = client.post(READY, json={"draft": draft, "extra_text": "", "covered_elsewhere": ["timing"]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body) == {"dimensions", "note"} and [d["id"] for d in body["dimensions"]] == IDS
    assert set(body["dimensions"][0]) == {"id", "status", "quote", "follow_up", "needs_author"}
    timing = next(d for d in body["dimensions"] if d["id"] == "timing")
    assert timing["follow_up"] is None


def test_route_validation_and_auth(client, monkeypatch):
    draft = client.post(f"{BASE}/idf/draft-text", json={"text": MANUSCRIPT}).json()
    assert client.post(READY, json={"draft": draft, "extra_text": "x" * 1501}).status_code == 422
    assert client.post(READY, json={"draft": draft, "covered_elsewhere": ["score"]}).status_code == 422
    assert client.post(READY, json={}).status_code == 422
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post(READY, json={"draft": draft}).status_code == 401
