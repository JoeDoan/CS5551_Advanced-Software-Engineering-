import base64
import io
import os
import subprocess
import tempfile

from PIL import Image
from pypdf import PdfReader

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IMAGES_DIR = os.path.join(REPO_ROOT, "docs", "images")
HACKATHON_DIR = os.path.join(REPO_ROOT, "docs", "hackathon")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPO_URL = "github.com/JoeDoan/CS5551_Advanced-Software-Engineering-"

# Held-out Spring 2026 (40 courses), from foia_replay_service._evaluate_against_heldout.
# (label, unseated seats, overflowed courses)
UNSEATED = [
    ("Copy prior term", 338, 8),
    ("Point forecast", 153, 9),
    ("OptiSched (80% bound)", 60, 2),
]
POINT_FORECAST_SEATS = UNSEATED[1][1]
OPTISCHED_SEATS = UNSEATED[2][1]
REDUCTION_VS_POINT_PCT = round(100 * (POINT_FORECAST_SEATS - OPTISCHED_SEATS) / POINT_FORECAST_SEATS)

# README screenshots: (output name, source screenshot, (x, y, width, height) in source pixels)
CROPS = [
    ("crop_forecast.png", "screenshot_forecast_benchmark.png", (305, 440, 1090, 465)),
    ("crop_whatif_presets.png", "screenshot_whatif_simulator.png", (309, 342, 1079, 89)),
    ("crop_whatif_result.png", "screenshot_whatif_simulator.png", (303, 888, 1090, 432)),
    ("crop_master_schedule.png", "screenshot_master_schedule.png", (281, 338, 1134, 598)),
]
# Poster-only crops. The master schedule keeps only course, time, room and instructor
# columns so they stay legible at print size, and is tall because the poster shows it
# top-aligned with object-fit: cover. The forecast crop drops the chart's footnotes.
POSTER_MASTER_CROP = ("screenshot_master_schedule.png", (281, 338, 800, 1400))
POSTER_FORECAST_CROP = ("screenshot_forecast_benchmark.png", (305, 440, 1090, 418))

CHART_W, CHART_H = 1200, 420


def make_crops() -> None:
    for out_name, src_name, (x, y, w, h) in CROPS:
        with Image.open(os.path.join(IMAGES_DIR, src_name)) as src:
            src.crop((x, y, x + w, y + h)).save(os.path.join(IMAGES_DIR, out_name))


def chart_svg() -> str:
    right = CHART_W - 40
    label_x = 370
    bar_x, bar_h = label_x + 20, 44
    bar_max = right - bar_x - 150
    scale = bar_max / max(seats for _, seats, _ in UNSEATED)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CHART_W} {CHART_H}" '
        f'width="100%" font-family="-apple-system, BlinkMacSystemFont, \'Helvetica Neue\', Arial, sans-serif">',
        f'<rect width="{CHART_W}" height="{CHART_H}" fill="#ffffff"/>',
        '<text x="40" y="58" font-size="26" font-weight="700" fill="#0f172a">'
        "Unseated students, held-out Spring 2026 (40 courses)</text>",
        f'<text x="{right}" y="62" text-anchor="end" font-size="48" font-weight="800" fill="#047857">'
        f"&#8722;{REDUCTION_VS_POINT_PCT}%</text>",
        f'<text x="{right}" y="90" text-anchor="end" font-size="16" font-weight="500" fill="#64748b">'
        f"vs point forecast ({POINT_FORECAST_SEATS} &#8594; {OPTISCHED_SEATS} seats)</text>",
    ]
    for i, (label, seats, overflowed) in enumerate(UNSEATED):
        cy = 160 + 80 * i
        is_ours = i == len(UNSEATED) - 1
        bar_w = round(seats * scale)
        parts += [
            f'<text x="{label_x}" y="{cy + 7}" text-anchor="end" font-size="20" font-weight="600" '
            f'fill="{"#047857" if is_ours else "#334155"}">{label}</text>',
            f'<rect x="{bar_x}" y="{cy - bar_h // 2}" width="{bar_w}" height="{bar_h}" rx="6" '
            f'fill="{"#059669" if is_ours else "#94a3b8"}"/>',
            f'<text x="{bar_x + bar_w + 12}" y="{cy + 8}" font-size="24" font-weight="800" fill="#0f172a">{seats}'
            f'<tspan dx="10" font-size="15" font-weight="500" fill="#64748b">'
            f"{overflowed} courses over</tspan></text>",
        ]
    parts += [
        '<text x="40" y="398" font-size="14" fill="#64748b">'
        "Unseated = enrollment above assigned room capacity. Baselines sized at +5%.</text>",
        "</svg>",
    ]
    return "".join(parts)


def poster_bars_html() -> str:
    """HTML bars instead of SVG so the rows can stretch to whatever height the panel has."""
    top = max(seats for _, seats, _ in UNSEATED)
    rows = []
    for i, (label, seats, overflowed) in enumerate(UNSEATED):
        is_ours = i == len(UNSEATED) - 1
        ours = " ours" if is_ours else ""
        delta = f' <b class="delta">&#8722;{REDUCTION_VS_POINT_PCT}% vs point</b>' if is_ours else ""
        rows.append(
            f'<div class="bar{ours}"><span class="bl">{label}</span>'
            f'<span class="track"><span class="fillbar" style="width:{0.45 * 100 * seats / top:.1f}%"></span>'
            f'<span class="bv"><b>{seats}</b> {overflowed} courses over{delta}</span></span></div>'
        )
    return "".join(rows)


COMPARISON_CHART_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  html, body { margin: 0; padding: 0; width: 1200px; height: 420px; overflow: hidden; background: #ffffff; }
  svg { display: block; width: 1200px; height: 420px; }
</style>
</head>
<body>{{CHART_SVG}}</body>
</html>
"""

POSTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>OptiSched Hack-A-Roo 2026 Poster</title>
<style>
  @page { size: letter landscape; margin: 0.25in; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --navy: #0f2a5c;
    --ink: #0f172a;
    --body: #334155;
    --muted: #64748b;
    --line: #dbe3ee;
    --green: #047857;
    --green-bg: #ecfdf5;
    --green-line: #a7f3d0;
    --amber: #b45309;
    --amber-bg: #fffbeb;
    --red: #b91c1c;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    color: var(--body);
    font-size: 8pt;
    line-height: 1.3;
  }
  .page { width: 1008px; height: 766px; overflow: hidden; display: flex; flex-direction: column; gap: 7px; }
  strong { color: var(--ink); }

  .banner { background: var(--navy); color: #fff; border-radius: 8px; padding: 9px 16px 8px; }
  .banner h1 { font-size: 15.6pt; font-weight: 800; letter-spacing: -0.015em; white-space: nowrap; }
  .banner .sub { font-size: 9.4pt; color: #dbeafe; margin-top: 3px; }
  .banner .row { display: flex; justify-content: space-between; align-items: baseline; margin-top: 3px; }
  .banner .byline { font-size: 8pt; color: #a5b4cf; }
  .banner .event { font-size: 10pt; font-weight: 800; }

  .hero { display: grid; grid-template-columns: 1.3fr 1fr 1fr 1fr; gap: 7px; }
  .stat {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 7px 11px;
    background: #fff;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .stat .n { font-size: 20pt; font-weight: 800; color: var(--navy); letter-spacing: -0.02em; line-height: 1; white-space: nowrap; }
  .stat .t { font-size: 8.4pt; font-weight: 700; color: var(--ink); line-height: 1.2; }
  .stat .d { font-size: 7.2pt; color: var(--muted); line-height: 1.25; }
  .stat.lead { background: var(--green-bg); border-color: var(--green-line); }
  .stat.lead .n { color: var(--green); font-size: 24pt; }

  .cols { flex: 1; min-height: 0; display: grid; grid-template-columns: 31fr 35fr 34fr; gap: 8px; }
  .col { display: flex; flex-direction: column; gap: 7px; min-height: 0; }
  .panel {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: #fff;
    padding: 8px 11px 9px;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .grow { flex: 1; }
  h2 { display: flex; align-items: center; gap: 7px; font-size: 10pt; font-weight: 800; color: var(--navy); margin-bottom: 6px; white-space: nowrap; }
  h2 i {
    font-style: normal;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--navy);
    color: #fff;
    font-size: 7.6pt;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  p + p { margin-top: 4px; }
  .label { font-size: 7pt; font-weight: 800; color: var(--muted); letter-spacing: 0.06em; text-transform: uppercase; margin: 7px 0 4px; }
  h2 + .label { margin-top: 0; }

  .flow { flex: 1; display: flex; flex-direction: column; justify-content: space-evenly; }
  .node { display: grid; grid-template-columns: 60px 1fr; gap: 8px; align-items: center; }
  .node b {
    text-align: center;
    background: #eff6ff;
    color: #1e40af;
    border: 1px solid #bfdbfe;
    border-radius: 5px;
    padding: 3px 0;
    font-size: 7.6pt;
    font-weight: 800;
  }
  .node.ours b { background: var(--green-bg); color: var(--green); border-color: var(--green-line); }
  .arrow { width: 0; height: 12px; margin-left: 30px; border-left: 1.5px solid #cbd5e1; font-size: 0; }

  .scope { display: flex; flex-direction: column; gap: 5px; }
  .box { border-radius: 6px; padding: 5px 8px 6px; font-size: 7.4pt; line-height: 1.3; }
  .box .tag { display: inline-block; font-size: 6.6pt; font-weight: 800; letter-spacing: 0.06em; border-radius: 3px; padding: 1px 5px; margin-right: 3px; color: #fff; }
  .real { background: var(--green-bg); border: 1px solid var(--green-line); }
  .real .tag { background: var(--green); }
  .sim { background: var(--amber-bg); border: 1px solid #fde68a; }
  .sim .tag { background: var(--amber); }
  .note { margin-top: 5px; font-size: 7.3pt; color: var(--muted); }

  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 7pt; font-weight: 700; color: var(--muted); padding: 0 5px 3px; border-bottom: 1.5px solid var(--line); }
  td { padding: 3px 5px; border-bottom: 1px solid #eef2f7; }
  tr:last-child td { border-bottom: none; }
  .c { text-align: center; }
  .num { text-align: right; white-space: nowrap; }
  td.num { font-weight: 700; color: var(--ink); }
  .yes { color: var(--green); font-weight: 800; }
  .no { color: var(--red); font-weight: 800; }
  .flat { color: var(--amber); font-weight: 700; }
  th.ours, td.ours { background: var(--green-bg); }
  th.ours { color: var(--green); }
  td.win { color: var(--green); }

  .bars { flex: 1; min-height: 90px; display: flex; flex-direction: column; justify-content: space-evenly; }
  .bar { display: grid; grid-template-columns: 128px 1fr; align-items: center; gap: 8px; }
  .bl { text-align: right; font-weight: 600; color: var(--body); white-space: nowrap; font-size: 7.8pt; }
  .track { height: 20px; display: flex; align-items: center; gap: 7px; }
  .fillbar { display: block; flex-shrink: 0; height: 100%; border-radius: 4px; background: #94a3b8; }
  .bv { font-size: 7.2pt; color: var(--muted); white-space: nowrap; }
  .bv b { font-size: 11pt; color: var(--ink); margin-right: 2px; }
  .bar.ours .bl { color: var(--green); font-weight: 800; }
  .bar.ours .fillbar { background: #059669; }
  .bv .delta { font-size: 9pt; color: var(--green); margin-left: 4px; }
  .foot { font-size: 7.2pt; color: var(--muted); margin-top: 4px; }

  .mae { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
  .mae div { border: 1px solid var(--line); border-radius: 6px; padding: 3px 8px 4px; }
  .mae b { display: block; font-size: 11.5pt; color: var(--ink); }
  .mae span { font-size: 7.1pt; color: var(--muted); }
  .mae .ours { background: var(--green-bg); border-color: var(--green-line); }
  .mae .ours b, .mae .ours span { color: var(--green); }
  .mae small { font-size: 8pt; font-weight: 700; }

  .benefit { margin-top: 7px; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .benefit div { background: #f1f5f9; border-radius: 6px; padding: 5px 8px; font-size: 7.6pt; }

  .shot { border: 1px solid var(--line); border-radius: 5px; overflow: hidden; background: #fff; }
  .shot img { display: block; width: 100%; }
  .shot.fill { flex: 1; min-height: 60px; position: relative; }
  .shot.fill img { position: absolute; inset: 0; height: 100%; object-fit: cover; object-position: top left; }
  .cap { font-size: 7.1pt; color: var(--muted); margin: 3px 0 0; }
  .scen td { font-size: 7.6pt; }
  .scen td:first-child { font-weight: 700; color: var(--ink); white-space: nowrap; }

  .footer { display: flex; justify-content: space-between; align-items: center; font-size: 7.4pt; color: var(--muted); padding: 0 4px; white-space: nowrap; }
  .footer b { color: var(--navy); }
  .footer .code { display: flex; align-items: center; gap: 8px; }
  .footer img { width: 40px; height: 40px; image-rendering: pixelated; }
  .footer code { font-family: "SF Mono", Menlo, monospace; font-size: 7pt; color: var(--body); }
  .footer .right { text-align: right; line-height: 1.45; }
  p, .cap, .note, .d, td, .foot { text-wrap: pretty; }
  .diff-note { margin-top: 6px; font-size: 7.6pt; }
  th.c, td:first-child, td.ours { white-space: nowrap; }
</style>
</head>
<body>
<div class="page">
  <div class="banner">
    <h1>OptiSched: Uncertainty-Aware Enrollment Forecasting with CP-SAT Course Scheduling</h1>
    <div class="sub">Size every room to a calibrated demand bound, then schedule it conflict-free.</div>
    <div class="row">
      <span class="byline">Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro &middot; Advisor: Prof. Yugyung Lee &middot; UMKC School of Science and Engineering</span>
      <span class="event">Hack-A-Roo 2026</span>
    </div>
  </div>

  <div class="hero">
    <div class="stat lead"><div class="n">&#8722;{{REDUCTION}}%</div><div><div class="t">unseated students</div><div class="d">{{POINT}} &#8594; {{OURS}} seats vs point forecast, at 64.9% seat use</div></div></div>
    <div class="stat"><div class="n">2/40</div><div><div class="t">courses overflow</div><div class="d">vs 8 prior term, 9 point forecast</div></div></div>
    <div class="stat"><div class="n">34/40</div><div><div class="t">inside 80% interval</div><div class="d">39/40 in 95% interval</div></div></div>
    <div class="stat"><div class="n">3/3</div><div><div class="t">What-If re-solves optimal</div><div class="d">0 hard conflicts in every solve</div></div></div>
  </div>

  <div class="cols">
    <div class="col">
      <div class="panel">
        <h2><i>1</i>Problem</h2>
        <p>Rooms are fixed months before registration. When demand outgrows a room, students start the term without a seat.</p>
        <p>On the held-out term, a point forecast fell short on <strong>19 of 40 courses</strong>.</p>
      </div>
      <div class="panel grow">
        <h2><i>2</i>Approach</h2>
        <div class="flow">
          <div class="node"><b>Forecast</b><div>Pooled ridge predicts next-term enrollment per course.</div></div>
          <div class="arrow">&#8595;</div>
          <div class="node"><b>Calibrate</b><div>Split-conformal 80% and 95% intervals from backtest errors.</div></div>
          <div class="arrow">&#8595;</div>
          <div class="node ours"><b>Size</b><div>Each course gets a room that fits its <strong>80% upper bound</strong>.</div></div>
          <div class="arrow">&#8595;</div>
          <div class="node"><b>Schedule</b><div>CP-SAT assigns room, time slot and instructor under hard constraints.</div></div>
          <div class="arrow">&#8595;</div>
          <div class="node"><b>Re-plan</b><div>What-If dry runs re-solve after a shock and list what moved.</div></div>
        </div>
      </div>
      <div class="panel">
        <h2><i>3</i>Data: real vs. simulated</h2>
        <div class="scope">
          <div class="box real"><span class="tag">REAL</span> UIUC registrar records (FOIA), 40 STEM courses &middot; train on 19 terms, Fall 2016 to Fall 2025 &middot; test on Spring 2026, held out &middot; 2-year faculty habits</div>
          <div class="box sim"><span class="tag">SIMULATED</span> 16-room pool behind the OptiSched utilization numbers &middot; preference weights 40/40/20 &middot; What-If scenarios</div>
        </div>
        <div class="note">Ten years of history predict one term ahead, not ten years out.</div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <h2><i>4</i>How it differs</h2>
        <table>
          <thead><tr><th></th><th class="c">Prior term</th><th class="c">Point forecast</th><th class="c ours">OptiSched</th></tr></thead>
          <tbody>
            <tr><td>Learns from history</td><td class="c no">1 term</td><td class="c yes">19 terms</td><td class="c yes ours">19 terms</td></tr>
            <tr><td>Per-course interval</td><td class="c no">no</td><td class="c no">no</td><td class="c yes ours">yes</td></tr>
            <tr><td>Room buffer</td><td class="c flat">flat +5%</td><td class="c flat">flat +5%</td><td class="c yes ours">80% bound</td></tr>
          </tbody>
        </table>
        <div class="diff-note">Standard timetabling tools treat enrollment as a fixed input. OptiSched schedules against a calibrated demand bound.</div>
      </div>
      <div class="panel grow">
        <h2><i>5</i>Results on held-out Spring 2026</h2>
        <div class="label">Students over room capacity, lower is better</div>
        <div class="bars">{{POSTER_BARS}}</div>
        <div class="foot">Baselines size rooms at forecast +5%.</div>
        <div class="label">Forecast error (MAE, seats)</div>
        <div class="mae">
          <div><b>28.25</b><span>copy prior term</span></div>
          <div><b>18.03</b><span>seasonal naive</span></div>
          <div class="ours"><b>17.24</b><span>pooled ridge</span></div>
        </div>
        <div class="foot">&#8722;39% vs prior term, &#8722;4% vs seasonal naive. The interval, not point accuracy, drives the gain.</div>
        <div class="label">Schedule quality</div>
        <table>
          <thead><tr><th></th><th class="num">OptiSched</th><th class="num">Actual UIUC</th></tr></thead>
          <tbody>
            <tr><td>Seat utilization</td><td class="num">64.9%</td><td class="num">64.5%</td></tr>
            <tr><td>Empty-seat waste</td><td class="num win">35.1%</td><td class="num">36.6%</td></tr>
            <tr><td>Faculty keep their usual slot</td><td class="num">84%</td><td class="num">n/a</td></tr>
          </tbody>
        </table>
        <div class="benefit">
          <div><strong>Students.</strong> Fewer seat shortages in week one.</div>
          <div><strong>Administrators.</strong> Fewer room moves after registration.</div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel grow">
        <h2><i>6</i>Working demonstration</h2>
        <div class="shot"><img src="{{IMG_FORECAST}}" alt="Demand forecast" /></div>
        <div class="cap">Live Fall 2026 forecast for STAT 400 with 80% and 95% intervals. Not part of the test.</div>
        <div class="label">What-If dry runs, live schedule untouched</div>
        <table class="scen">
          <tbody>
            <tr><td>Enrollment surge</td><td>CS +20%, STAT +15%. 2 courses move to larger rooms.</td></tr>
            <tr><td>Instructor unavailable</td><td>Only STAT 420 moves, to a qualified colleague.</td></tr>
            <tr><td>Room capacity &times;0.9</td><td>3 courses move to rooms that fit.</td></tr>
          </tbody>
        </table>
        <div class="label">Master schedule</div>
        <div class="shot fill"><img src="{{IMG_MASTER}}" alt="Master schedule" /></div>
        <div class="cap">40 sections with room, time and instructor.</div>
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="code"><img src="{{IMG_QR}}" alt="Repository QR code" /><div><b>Code</b> &nbsp;{{REPO_URL}}<br/><b>Reproduce</b> &nbsp;<code>pytest backend/tests/test_uiuc_foia_replay.py</code></div></div>
    <div class="right">FastAPI &middot; OR-Tools CP-SAT &middot; React + TypeScript &middot; 353 automated tests<br/><b>Extension</b> &nbsp;Faculty Commercialization Advisor (UM-16C disclosures)</div>
  </div>
</div>
</body>
</html>
"""


def data_uri(png_name: str) -> str:
    with open(os.path.join(IMAGES_DIR, png_name), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")


def poster_crop_uri(crop: tuple) -> str:
    src_name, (x, y, w, h) = crop
    buf = io.BytesIO()
    with Image.open(os.path.join(IMAGES_DIR, src_name)) as src:
        src.crop((x, y, x + w, y + h)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def poster_html() -> str:
    return (
        POSTER_HTML.replace("{{POSTER_BARS}}", poster_bars_html())
        .replace("{{REDUCTION}}", str(REDUCTION_VS_POINT_PCT))
        .replace("{{POINT}}", str(POINT_FORECAST_SEATS))
        .replace("{{OURS}}", str(OPTISCHED_SEATS))
        .replace("{{IMG_MASTER}}", poster_crop_uri(POSTER_MASTER_CROP))
        .replace("{{IMG_FORECAST}}", poster_crop_uri(POSTER_FORECAST_CROP))
        .replace("{{IMG_QR}}", data_uri("repo_qr.png"))
        .replace("{{REPO_URL}}", REPO_URL)
    )


def main() -> None:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(HACKATHON_DIR, exist_ok=True)
    make_crops()

    with tempfile.TemporaryDirectory() as tmpdir:
        chart_html_path = os.path.join(tmpdir, "comparison_chart.html")
        chart_png_path = os.path.join(IMAGES_DIR, "unseated_students_comparison.png")
        with open(chart_html_path, "w", encoding="utf-8") as fh:
            fh.write(COMPARISON_CHART_HTML.replace("{{CHART_SVG}}", chart_svg()))

        subprocess.run(
            [
                CHROME_BIN,
                "--headless",
                f"--user-data-dir={os.path.join(tmpdir, 'chrome-profile')}",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                f"--window-size={CHART_W},{CHART_H}",
                f"--screenshot={chart_png_path}",
                f"file://{chart_html_path}",
            ],
            check=True,
        )

        poster_html_path = os.path.join(tmpdir, "hackaroo_poster.html")
        with open(poster_html_path, "w", encoding="utf-8") as fh:
            fh.write(poster_html())

        poster_pdf_path = os.path.join(HACKATHON_DIR, "OptiSched_HackARoo_Poster.pdf")
        subprocess.run(
            [
                CHROME_BIN,
                "--headless",
                f"--user-data-dir={os.path.join(tmpdir, 'chrome-profile')}",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={poster_pdf_path}",
                f"file://{poster_html_path}",
            ],
            check=True,
        )

    reader = PdfReader(poster_pdf_path)
    assert len(reader.pages) == 1, f"Expected 1-page poster, got {len(reader.pages)}"
    print("Generated crops, chart PNG and 1-page poster PDF successfully.")


if __name__ == "__main__":
    main()
