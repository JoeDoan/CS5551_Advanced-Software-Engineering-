import json
from collections import Counter

import pytest

from app.services import glossary_service as g
from app.services.verifier import claims_filter
from tests.test_commercialization import BASE

IDF_FIELDS = json.load(open(g.GLOSSARY_PATH.parents[2] / "data" / "policies" / "idf_fields.json", encoding="utf-8"))["fields"]
SPONSOR_TERMS = {
    "novelty", "prior_art", "inventorship", "public_disclosure", "translational_readiness",
    "potential_application", "differentiation", "development_stage",
}


def test_glossary_covers_every_concept_the_sponsor_named():
    ids = {e.id for e in g.list_entries()}
    assert SPONSOR_TERMS <= ids
    assert {"conflict_of_interest", "invention_disclosure", "disclosure"} <= ids


def test_ids_and_aliases_are_unique_so_a_lookup_cannot_be_ambiguous():
    entries = g.list_entries()
    assert len({e.id for e in entries}) == len(entries)
    aliases = Counter(a.lower() for e in entries for a in e.aliases)
    assert [a for a, n in aliases.items() if n > 1] == []


def test_links_point_at_real_entries_and_real_form_fields():
    ids = {e.id for e in g.list_entries()}
    field_ids = {f["id"] for f in IDF_FIELDS}
    for e in g.list_entries():
        assert set(e.related) <= ids and e.id not in e.related, e.id
        assert set(e.related_fields) <= field_ids, e.id


def test_entries_are_complete_and_pass_the_claims_filter():
    for e in g.list_entries():
        assert e.plain and e.example and e.think_about, e.id
        assert claims_filter(" ".join([e.plain, e.example, *e.think_about])) == [], e.id


def test_every_entry_says_it_is_a_draft_until_someone_reviews_it():
    for e in g.list_entries():
        assert e.reviewed_by is None and e.reviewed_on is None
        assert e.source_label == g.SOURCE_DRAFT
    assert "not yet reviewed" in g.SOURCE_DRAFT


def test_a_reviewed_entry_names_the_reviewer_and_date(monkeypatch):
    raw = [dict(r) for r in g._raw_entries()]
    raw[0]["reviewed_by"], raw[0]["reviewed_on"] = "the Office of Technology Commercialization", "2026-12-01"
    monkeypatch.setattr(g, "_raw_entries", lambda: raw)
    label = g.list_entries()[0].source_label
    assert "reviewed by the Office of Technology Commercialization on 2026-12-01" in label


@pytest.mark.parametrize(
    "q,expected",
    [
        ("What is a conflict of interest?", ["conflict_of_interest"]),
        ("What is novelty?", ["novelty"]),
        ("novelty", ["novelty"]),
        ("What does patentable mean?", ["patentability"]),
        ("What does 'translational readiness' mean?", ["translational_readiness"]),
        ("Define inventorship", ["inventorship"]),
        ("What is an inventor?", ["inventorship"]),
        ("What's an invention disclosure?", ["invention_disclosure"]),
        ("What is a disclosure?", ["disclosure"]),
        ("What is the difference between novelty and prior art?", ["novelty", "prior_art"]),
        ("Explain public disclosure", ["public_disclosure"]),
    ],
)
def test_definitional_questions_find_their_entry(q, expected):
    assert [e.id for e in g.lookup(q)] == expected


@pytest.mark.parametrize(
    "q",
    [
        "Who owns an invention I make using university resources?",  # a policy question that merely mentions a term
        "Do I have to report outside consulting for a company?",
        "What is a patent?",  # no glossary entry; goes to the policy search instead
        "What is the weather in Kansas City?",
        "How do I disclose an invention?",
    ],
)
def test_other_questions_do_not_match(q):
    assert g.lookup(q) == []


def test_policy_quotes_attach_to_entries_that_map_one_and_only_when_real():
    for e in g.list_entries():
        blocks = g.to_block(e)
        assert blocks[0].type == "glossary" and blocks[0].source_label == g.SOURCE_DRAFT
        for b in blocks[1:]:
            assert b.type == "policy_quote" and 0 < len(b.citations) <= g.MAX_QUOTES_WITH_ENTRY
    coi = g.to_block(g.get("conflict_of_interest"))
    assert [b.type for b in coi] == ["glossary", "policy_quote"]
    assert len(coi[1].citations) == 1 and "Financial Conflict of Interest" in coi[1].citations[0].text  # a real definition
    assert [b.type for b in g.to_block(g.get("novelty"))] == ["glossary"]  # no mapped policy, so no quote


def test_glossary_route_lists_entries(client):
    res = client.get(f"{BASE}/glossary")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == len(g.list_entries())
    assert {"id", "term", "aliases", "plain", "example", "think_about", "related_fields", "related",
            "reviewed_by", "reviewed_on", "source_label"} == set(body[0])


def test_glossary_route_requires_login_when_auth_is_on(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.get(f"{BASE}/glossary").status_code == 401
