import httpx

from app.services import lookup_adapters
from app.services.lookup_adapters import LookupRequest, run_lookup
from tests.test_commercialization import BASE


def test_fixture_mode_is_the_default_and_matches_broad_terms(monkeypatch):
    monkeypatch.delenv("COMMERCIALIZATION_LIVE", raising=False)
    res = run_lookup(LookupRequest(terms=["Acoustic Sensing", "bridge inspection"]))
    assert res.mode == "fixture" and res.items
    assert res.terms == ["acoustic sensing", "bridge inspection"]
    assert "not a novelty or patentability finding" in res.note
    assert "patent search is included" in res.note


def test_unknown_terms_say_so_instead_of_inventing_results(monkeypatch):
    monkeypatch.delenv("COMMERCIALIZATION_LIVE", raising=False)
    res = run_lookup(LookupRequest(terms=["quantum gravity"]))
    assert res.items == [] and "No saved results" in res.message


def test_terms_are_validated_as_short_broad_phrases(client):
    bad = [
        [],
        ["a", "b", "c", "d", "e", "f"],
        ["low cost passive acoustic sensing of cracks"],
        ["x" * 31],
        ["drop table; --"],
    ]
    for terms in bad:
        assert client.post(f"{BASE}/lookup", json={"terms": terms}).status_code == 422, terms
    assert client.post(f"{BASE}/lookup", json={}).status_code == 422


def test_live_mode_sends_only_the_terms_and_falls_back_on_failure(monkeypatch):
    monkeypatch.setenv("COMMERCIALIZATION_LIVE", "true")
    sent = []

    def ok(term, client):
        sent.append(term)
        return [lookup_adapters.LookupItem(kind="literature", title=f"Paper on {term}", source="OpenAlex")]

    monkeypatch.setattr(lookup_adapters, "fetch_literature", ok)
    monkeypatch.setattr(lookup_adapters, "fetch_awards", lambda term, client: [])
    res = run_lookup(LookupRequest(terms=["acoustic sensing"]))
    assert res.mode == "live" and sent == ["acoustic sensing"] and res.items[0].title == "Paper on acoustic sensing"

    def boom(term, client):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(lookup_adapters, "fetch_literature", boom)
    res = run_lookup(LookupRequest(terms=["acoustic sensing"]))
    assert res.mode == "fixture" and "Live search failed" in res.message and res.items


def test_lookup_route_and_auth(client, monkeypatch):
    monkeypatch.delenv("COMMERCIALIZATION_LIVE", raising=False)
    res = client.post(f"{BASE}/lookup", json={"terms": ["machine learning"]})
    assert res.status_code == 200 and res.json()["items"]
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post(f"{BASE}/lookup", json={"terms": ["machine learning"]}).status_code == 401
