import io
import json
import os
import zipfile

from app.services.export_service import FILES, NOTICE, ExportRequest, build_export
from app.services.idf_service import draft_idf
from tests.test_commercialization import BASE, MANUSCRIPT


def _zip(draft, answers=None) -> zipfile.ZipFile:
    data = build_export(ExportRequest(draft=draft, answers=answers or {}))
    return zipfile.ZipFile(io.BytesIO(data))


def test_package_has_the_six_files_and_every_text_file_carries_the_notice():
    z = _zip(draft_idf(MANUSCRIPT), {"students": "yes"})
    assert z.namelist() == list(FILES)
    for name in FILES:
        assert NOTICE in z.read(name).decode("utf-8"), name


def test_idf_draft_keeps_evidence_and_leaves_human_fields_blank():
    draft = draft_idf(MANUSCRIPT)
    z = _zip(draft)
    md = z.read(FILES[0]).decode("utf-8")
    assert "Blank: the author completes this." in md
    proposed = next(f for f in draft.fields if f.status == "proposed" and f.evidence)
    assert proposed.evidence in md
    assert "<!doctype html>" in z.read(FILES[1]).decode("utf-8")


def test_html_escapes_text_from_the_paper():
    draft = draft_idf(MANUSCRIPT)
    draft.fields[0].value = "<script>alert(1)</script>"
    page = _zip(draft).read(FILES[1]).decode("utf-8")
    assert "<script>" not in page and "&lt;script&gt;" in page


def test_checklist_file_quotes_policy_and_summary_uses_only_title_and_description():
    draft = draft_idf(MANUSCRIPT)
    z = _zip(draft, {"students": "yes"})
    checklist = z.read(FILES[3]).decode("utf-8")
    assert "Students" in checklist or "student" in checklist
    assert "> \"" in checklist and "not legal advice" in checklist.lower()
    summary = z.read(FILES[4]).decode("utf-8")
    technical = next((f.value for f in draft.fields if f.id == "A1_technical"), "")
    if technical:
        assert technical not in summary


def test_bundle_json_round_trips_the_draft_and_answers():
    draft = draft_idf(MANUSCRIPT)
    bundle = json.loads(_zip(draft, {"public": "no"}).read(FILES[5]))
    assert bundle["answers"] == {"public": "no"}
    assert len(bundle["draft"]["fields"]) == len(draft.fields)


def test_export_route_returns_a_zip_writes_nothing_and_requires_auth(client, monkeypatch, tmp_path):
    draft = client.post(f"{BASE}/idf/draft-text", json={"text": MANUSCRIPT}).json()
    before = set(os.listdir(os.getcwd()))
    res = client.post(f"{BASE}/export", json={"draft": draft, "answers": {}})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "attachment" in res.headers["content-disposition"]
    assert zipfile.ZipFile(io.BytesIO(res.content)).namelist() == list(FILES)
    assert set(os.listdir(os.getcwd())) == before
    assert client.post(f"{BASE}/export", json={"answers": {}}).status_code == 422

    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post(f"{BASE}/export", json={"draft": draft, "answers": {}}).status_code == 401
