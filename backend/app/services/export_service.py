"""Export package: the draft, checklist and market notes as a zip built in memory.

Standard library only (io, zipfile, html, json). Nothing is written to disk and nothing is
stored: the bytes are returned to the caller. Every text file carries the same notice that
this is a draft the author must verify. Contents come from the draft and the author's
answers; checklist and market sections are recomputed by the same deterministic services.
"""

import html
import io
import json
import zipfile
from typing import Dict, List

from pydantic import BaseModel

from app.services.coi_checklist_service import ChecklistRequest, build_checklist
from app.services.idf_service import DraftResponse
from app.services.matcher_service import match_industries

NOTICE = "Draft prepared with OptiSched. The author must verify every entry. Not legal advice."
SUMMARY_FIELDS = ("A1_title", "A1_general")
MARKET_FIELDS = ("A1_title", "A1_general", "A1_technical", "A1_novel", "A1_problem", "A1_keywords")

FILES = (
    "01_UM16C_Draft_IDF.md",
    "01_UM16C_Draft_IDF.html",
    "02_Prior_Art_and_Market_Report.md",
    "03_COI_Compliance_Checklist_Cited.md",
    "04_Non_Confidential_Summary_1Page.md",
    "05_raw_submission_bundle.json",
)


class ExportRequest(BaseModel):
    draft: DraftResponse
    answers: Dict[str, str] = {}


def _value(draft: DraftResponse, field_id: str) -> str:
    return next((f.value for f in draft.fields if f.id == field_id), "")


def _sections(draft: DraftResponse) -> Dict[str, list]:
    out: Dict[str, list] = {}
    for f in draft.fields:
        out.setdefault(f.section, []).append(f)
    return out


def _status_label(status: str) -> str:
    return {"proposed": "Proposed from your paper", "needs_author": "Please confirm", "blank": "For you to fill in"}[status]


def build_idf_markdown(draft: DraftResponse) -> str:
    lines = ["# Draft Invention Disclosure (UM-16C sections)", "", f"_{NOTICE}_", ""]
    for flag in draft.flags:
        lines.append(f"> **{flag.level.title()}:** {flag.message}")
    if draft.flags:
        lines.append("")
    for section, fields in _sections(draft).items():
        lines += [f"## {section}", ""]
        for f in fields:
            lines.append(f"### {f.label}")
            lines.append(f"*{_status_label(f.status)}*")
            lines.append("")
            lines.append(f.value if f.value else "_Blank: the author completes this._")
            if f.evidence:
                lines += ["", f"Evidence from your paper: \"{f.evidence}\""]
            if f.note:
                lines += ["", f"Note: {f.note}"]
            lines.append("")
    lines += [f"Official form: {draft.form_url}", f"Return to: {draft.returns_to}", ""]
    return "\n".join(lines)


_HTML_CSS = (
    "body{font-family:Georgia,serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#111}"
    "h1{font-size:1.5rem}h2{font-size:1.2rem;border-bottom:1px solid #999;margin-top:1.6rem}"
    "h3{font-size:1rem;margin-bottom:.2rem}.s{color:#555;font-size:.85rem;margin:0}"
    ".n,.e{font-size:.85rem;color:#444}.f{border:1px solid #bbb;padding:.4rem .7rem;margin:.8rem 0}"
    "@media print{body{margin:0}.f{page-break-inside:avoid}}"
)


def build_idf_html(draft: DraftResponse) -> str:
    esc = html.escape
    out = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<title>Draft Invention Disclosure</title>",
        f"<style>{_HTML_CSS}</style></head><body>",
        "<h1>Draft Invention Disclosure (UM-16C sections)</h1>",
        f"<p><em>{esc(NOTICE)}</em></p>",
    ]
    for flag in draft.flags:
        out.append(f"<p><strong>{esc(flag.level.title())}:</strong> {esc(flag.message)}</p>")
    for section, fields in _sections(draft).items():
        out.append(f"<h2>{esc(section)}</h2>")
        for f in fields:
            body = esc(f.value) if f.value else "<em>Blank: the author completes this.</em>"
            out.append(f"<div class=\"f\"><h3>{esc(f.label)}</h3><p class=\"s\">{esc(_status_label(f.status))}</p>")
            out.append(f"<p>{body}</p>")
            if f.evidence:
                out.append(f"<p class=\"e\">Evidence from your paper: &ldquo;{esc(f.evidence)}&rdquo;</p>")
            if f.note:
                out.append(f"<p class=\"n\">Note: {esc(f.note)}</p>")
            out.append("</div>")
    out.append(f"<p>Official form: {esc(draft.form_url)}<br>Return to: {esc(draft.returns_to)}</p>")
    out.append("</body></html>")
    return "".join(out)


def build_market_markdown(draft: DraftResponse) -> str:
    text = ". ".join(v for v in (_value(draft, i) for i in MARKET_FIELDS) if v)
    lines = ["# Market and prior-art notes", "", f"_{NOTICE}_", ""]
    if len(text) < 20:
        return "\n".join(lines + ["Not enough drafted text to suggest markets.", ""])
    match = match_industries(text)
    lines += ["## Possible target applications (hypotheses to test, not findings)", "", match.message, ""]
    for i, m in enumerate(match.matches, 1):
        lines += [
            f"### {i}. {m.name}",
            f"Your text mentions: {', '.join(m.matched_terms)}",
            "",
            "Pain points to test:",
            *[f"- {p}" for p in m.pain_points],
            "",
            "Who might buy:",
            *[f"- {b}" for b in m.buyer_types],
            "",
            "NAICS: " + "; ".join(f"{n.code} {n.title}" for n in m.naics),
            "SBIR/STTR agencies: " + ", ".join(m.sbir_agencies),
            "",
        ]
    lines += [
        "## Prior art",
        "",
        "No prior-art or grant lookup is included in this package. This tool does not decide "
        "whether anything is novel or patentable.",
        "",
        match.note,
        f"SBIR topics: {match.sbir_topics_url}",
        "",
    ]
    return "\n".join(lines)


def build_checklist_markdown(draft: DraftResponse, answers: Dict[str, str]) -> str:
    result = build_checklist(ChecklistRequest(draft=draft, answers=answers))
    lines = ["# Compliance checklist with policy citations", "", f"_{NOTICE}_", ""]
    for item in result.items:
        lines += [f"## {item.title} ({'to do' if item.status == 'action' else 'review'})", "", item.why, ""]
        lines += [f"- {a}" for a in item.actions]
        lines += [f"- Link: {link.label} {link.url}" for link in item.links]
        for c in item.citations:
            where = " | ".join(x for x in (c.section, c.locator) if x)
            lines += ["", f"> \"{c.text}\"", f"> {c.source_title}, {c.version}. {where}. {c.source_url}"]
        lines.append("")
    lines += [result.disclaimer, ""]
    return "\n".join(lines)


def build_summary_markdown(draft: DraftResponse) -> str:
    title = _value(draft, "A1_title") or "Untitled technology"
    general = _value(draft, "A1_general")
    lines = [f"# {title}", "", f"_{NOTICE}_", ""]
    lines.append(general or "The author has not yet written a general description.")
    lines += [
        "",
        "Built from the title and general description only. Read it before sharing to make sure it "
        "leaves out anything confidential or unpublished.",
        "",
    ]
    return "\n".join(lines)


def build_bundle_json(draft: DraftResponse, answers: Dict[str, str]) -> str:
    return json.dumps(
        {"notice": NOTICE, "draft": draft.model_dump(), "answers": answers}, indent=2, ensure_ascii=False
    )


def build_export(req: ExportRequest) -> bytes:
    contents: List[tuple] = [
        (FILES[0], build_idf_markdown(req.draft)),
        (FILES[1], build_idf_html(req.draft)),
        (FILES[2], build_market_markdown(req.draft)),
        (FILES[3], build_checklist_markdown(req.draft, req.answers)),
        (FILES[4], build_summary_markdown(req.draft)),
        (FILES[5], build_bundle_json(req.draft, req.answers)),
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in contents:
            z.writestr(name, text.encode("utf-8"))
    return buf.getvalue()
