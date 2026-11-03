"""Build the policy corpus used by the faculty commercialization guardrail.

Reads the public policy sources saved in docs/policies/raw/ and writes
backend/data/policies/corpus.json: short, citable passages, each carrying its
source title, URL, version note and a section / page locator.

Run once, then commit corpus.json (not the raw downloads):
    python backend/data/scripts/build_policy_corpus.py

Needs pypdf for the one PDF; the runtime app does not.
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "docs" / "policies" / "raw"
OUT = ROOT / "backend" / "data" / "policies" / "corpus.json"

MAX_CHARS = 900
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}
SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "form", "svg"}

SOURCES = [
    {
        "id": "um-crr-330-015",
        "file": "um_330_015_coi.html",
        "title": "UM Collected Rules 330.015, Policy on Conflict of Interest",
        "url": "https://www.umsystem.edu/ums/rules/collected_rules/personnel/ch330/330.015_policy_on_conflict_of_interest",
        "version": "Amended 9-12-24",
        "scope": "All University of Missouri System employees",
    },
    {
        "id": "um-crr-420-030",
        "file": "um_420_030_federal.html",
        "title": "UM Collected Rules 420.030, Conflict with the Interests of Federal Grant Agencies",
        "url": "https://www.umsystem.edu/ums/rules/collected_rules/research/ch420/420.030_conflict_with_the_interests_of_federal_grant_agencies",
        "version": "Amended 8-24-12",
        "scope": "Investigators on NSF or PHS (including NIH) funded or proposed research",
    },
    {
        "id": "um-crr-100-020",
        "file": "um_100_020_inventions.html",
        "title": "UM Collected Rules 100.020, Invention and Patent Regulations",
        "url": "https://www.umsystem.edu/policies/collected-rules/business-management/chapter-100-patent-copyright-law/100020-invention-patent-regulations",
        "version": "Amended 6-24-21",
        "scope": "University employees and enrolled students",
    },
    {
        "id": "um-crr-100-030",
        "file": "um_100_030_copyright.html",
        "title": "UM Collected Rules 100.030, Copyright Regulations",
        "url": "https://www.umsystem.edu/policies/collected-rules/business-management/chapter-100-patent-copyright-law/100030-copyright-regulations",
        "version": "Amended 6-24-21",
        "scope": "University employees, students and others using University resources",
    },
    {
        "id": "umkc-fcoi",
        "file": "fcoi_umkc.pdf",
        "title": "UMKC Financial Conflict of Interest (FCOI) Policy",
        "url": "https://ori.umkc.edu/policy-and-forms/conflict-of-interest/revised-fcoi_policy-062422026-003-umkc.pdf",
        "version": "Version June 2026",
        "scope": "UMKC investigators",
    },
    {
        "id": "umkc-ownership",
        "file": "umkc_ownership.html",
        "title": "UMKC Office of Research and Innovation, Ownership",
        "url": "https://ori.umkc.edu/facilities-compliance-and-commercialization/commercialization/ownership.php",
        "version": "Web page, retrieved 2026-11-01",
        "scope": "UMKC inventors",
    },
    {
        "id": "umkc-ip",
        "file": "umkc_ip.html",
        "title": "UMKC Office of Research and Innovation, Intellectual Property",
        "url": "https://ori.umkc.edu/facilities-compliance-and-commercialization/commercialization/intellectual-property.php",
        "version": "Web page, retrieved 2026-11-01",
        "scope": "UMKC inventors",
    },
]


class _Blocks(HTMLParser):
    """Collect (tag, text) for headings, paragraphs and list items, in order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self._skip = 0
        self._tag = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag in BLOCK_TAGS and not self._skip:
            self._flush()
            self._tag = tag

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in BLOCK_TAGS and not self._skip:
            self._flush()

    def handle_data(self, data):
        if self._tag and not self._skip:
            self._buf.append(data)

    def _flush(self):
        text = re.sub(r"\s+", " ", html.unescape("".join(self._buf))).strip()
        if self._tag and text:
            self.blocks.append((self._tag, text))
        self._tag, self._buf = None, []


def _html_sections(path):
    parser = _Blocks()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    parser.close()
    heading, out = "", []
    for tag, text in parser.blocks:
        if tag.startswith("h"):
            heading = text
        elif len(text) > 40:
            out.append((heading, text))
    return out


def _pdf_sections(path):
    from pypdf import PdfReader

    out, heading = [], ""
    for page_no, page in enumerate(PdfReader(str(path)).pages, start=1):
        raw = page.extract_text() or ""
        # Roman-numeral section headings can sit mid-paragraph; isolate them first.
        raw = re.sub(r"(?m)^\s*([IVX]+\.\s+[A-Z][A-Z ,/&'-]{3,}?):?\s*$", r"\n\n@@H@@\1\n\n", raw)
        for para in re.split(r"\n\s*\n|(?<=[.:;])\s*\n(?=[A-Z0-9(@])", raw):
            found = re.match(r"^\s*@@H@@(.+?)\s*(?:\n|$)", para)
            if found:
                heading = found.group(1).strip()
                para = para[found.end():]
            text = re.sub(r"\s+", " ", para).strip()
            if len(text) > 40 and not re.fullmatch(r"\d+\s+Version.*", text):
                out.append((heading, text, page_no))
    return out


def _chunk(text):
    """Split long text on sentence boundaries so each passage stays quotable."""
    if len(text) <= MAX_CHARS:
        return [text]
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        if cur and len(cur) + len(sentence) > MAX_CHARS:
            parts.append(cur.strip())
            cur = ""
        cur += sentence + " "
    if cur.strip():
        parts.append(cur.strip())
    return parts


def build():
    passages = []
    for src in SOURCES:
        path = RAW / src["file"]
        if src["file"].endswith(".pdf"):
            rows = [(h, t, f"p. {p}") for h, t, p in _pdf_sections(path)]
        else:
            rows = [(h, t, h or "") for h, t in _html_sections(path)]
        n = 0
        for heading, text, locator in rows:
            for piece in _chunk(text):
                n += 1
                passages.append(
                    {
                        "id": f"{src['id']}#{n}",
                        "source_id": src["id"],
                        "source_title": src["title"],
                        "source_url": src["url"],
                        "version": src["version"],
                        "applies_to": src["scope"],
                        "section": heading,
                        "locator": locator,
                        "text": piece,
                    }
                )
        print(f"{src['id']}: {n} passages")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "note": "Passages are verbatim extracts of public University of Missouri / UMKC "
                "documents. This is not legal advice. Confirm with the UMKC COI Office "
                "(umkccoi@umkc.edu) and the Office of Technology Commercialization.",
                "retrieved": "2026-11-01",
                "passages": passages,
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(passages)} passages to {OUT}")


if __name__ == "__main__":
    build()
