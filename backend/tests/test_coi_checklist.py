import json

from app.services.clarify_service import build_questions
from app.services.coi_checklist_service import ChecklistRequest, build_checklist
from app.services.idf_service import draft_idf
from app.services.policy_service import CORPUS_PATH
from tests.test_commercialization import BASE, MANUSCRIPT

# A manuscript with no stated funding, dates or keywords.
BARE = (
    "A Study of Compressed Sensing for Sparse Signals\nJane Researcher\n"
    + "We analyze how many measurements are needed to recover sparse signals. " * 12
)

ALL_YES = {
    "outside_interest": "yes", "students": "yes", "course_release": "yes",
    "third_party": "yes", "public": "yes",
}


def _corpus():
    return {p["id"]: p for p in json.load(open(CORPUS_PATH, encoding="utf-8"))["passages"]}


def test_questions_are_few_targeted_and_use_the_drafts_own_gaps():
    questions = build_questions(draft_idf(MANUSCRIPT)).questions
    ids = [q.id for q in questions]
    assert 3 <= len(ids) <= 5 and len(set(ids)) == len(ids)
    assert ids[0] == "public" and "March 3, 2025" in questions[0].text
    assert "funding" not in ids  # the manuscript already names its funder
    assert all(q.why and "unsure" in {o.value for o in q.options} for q in questions)

    bare = [q.id for q in build_questions(draft_idf(BARE)).questions]
    assert "funding" in bare and len(bare) == 5
    assert build_questions(draft_idf(BARE)).questions[0].text.startswith("Have you presented")


def test_checklist_cites_real_policy_text_verbatim():
    corpus = _corpus()
    items = build_checklist(ChecklistRequest(draft=draft_idf(MANUSCRIPT), answers=ALL_YES)).items
    ids = {i.id for i in items}
    assert {"outside_interest", "students", "federal_funding", "public_disclosure",
            "course_release", "third_party", "annual_disclosure"} <= ids
    for item in items:
        assert item.actions and item.links and item.why
        for c in item.citations:
            assert c.text == corpus[c.passage_id]["text"] and c.version and c.source_url.startswith("https://")
    students = next(i for i in items if i.id == "students")
    assert any("100.020" in c.source_title or "Ownership" in c.source_title for c in students.citations)
    # items that rest on UMKC's guidance or the form, not on a policy passage, never fake a citation
    assert next(i for i in items if i.id == "public_disclosure").citations == []
    assert next(i for i in items if i.id == "third_party").citations == []


def test_only_triggered_items_appear_and_the_buyout_tool_follows_the_answer():
    base = build_checklist(ChecklistRequest(draft=draft_idf(BARE), answers={})).items
    assert [i.id for i in base] == ["annual_disclosure"] and base[0].status == "review"

    no = build_checklist(ChecklistRequest(draft=draft_idf(BARE), answers={"outside_interest": "no", "students": "no"}))
    assert [i.id for i in no.items] == ["annual_disclosure"]

    release = build_checklist(ChecklistRequest(draft=draft_idf(BARE), answers={"course_release": "yes"})).items
    assert next(i for i in release if i.id == "course_release").tool == "buyout"
    assert all(i.tool is None for i in base)


def test_federal_funding_item_comes_from_the_draft_or_the_answer():
    from_draft = build_checklist(ChecklistRequest(draft=draft_idf(MANUSCRIPT), answers={})).items
    assert "federal_funding" in {i.id for i in from_draft}
    from_answer = build_checklist(ChecklistRequest(draft=draft_idf(BARE), answers={"funding": "federal"})).items
    assert "federal_funding" in {i.id for i in from_answer}
    none = build_checklist(ChecklistRequest(draft=draft_idf(BARE), answers={"funding": "none"})).items
    assert "federal_funding" not in {i.id for i in none}


def test_clarify_and_checklist_routes(client, monkeypatch):
    draft = client.post(f"{BASE}/idf/draft-text", json={"text": MANUSCRIPT}).json()
    q = client.post(f"{BASE}/clarify", json=draft)
    assert q.status_code == 200 and q.json()["questions"][0]["id"] == "public"
    c = client.post(f"{BASE}/checklist", json={"draft": draft, "answers": {"students": "yes"}})
    assert c.status_code == 200
    assert {"students", "annual_disclosure"} <= {i["id"] for i in c.json()["items"]}
    assert "not legal advice" in c.json()["disclaimer"]
    assert client.post(f"{BASE}/checklist", json={"answers": {}}).status_code == 422

    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post(f"{BASE}/clarify", json=draft).status_code == 401
    assert client.post(f"{BASE}/checklist", json={"draft": draft, "answers": {}}).status_code == 401
