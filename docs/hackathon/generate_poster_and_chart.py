import base64
import os
import subprocess
import tempfile

import fitz
from PIL import Image

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IMAGES_DIR = os.path.join(REPO_ROOT, "docs", "images")
HACKATHON_DIR = os.path.join(REPO_ROOT, "docs", "hackathon")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPO_URL = "github.com/JoeDoan/CS5551_Advanced-Software-Engineering-"

UNSEATED = [
    ("Copy prior term (+5%)", 338, 8, "#dc2626", "#fef2f2"),
    ("Point forecast (+5%)", 153, 9, "#d97706", "#fffbeb"),
    ("OptiSched (80% bound)", 60, 2, "#059669", "#ecfdf5"),
]
PRIOR_TERM_SEATS = UNSEATED[0][1]
POINT_FORECAST_SEATS = UNSEATED[1][1]
OPTISCHED_SEATS = UNSEATED[2][1]
REDUCTION_VS_POINT_PCT = round(100 * (POINT_FORECAST_SEATS - OPTISCHED_SEATS) / POINT_FORECAST_SEATS)
REDUCTION_VS_PRIOR_PCT = round(100 * (PRIOR_TERM_SEATS - OPTISCHED_SEATS) / PRIOR_TERM_SEATS)

CROPS = [
    ("crop_forecast.png", "screenshot_forecast_benchmark.png", (305, 440, 1090, 465)),
    ("crop_whatif_presets.png", "screenshot_whatif_simulator.png", (309, 342, 1079, 89)),
    ("crop_whatif_result.png", "screenshot_whatif_simulator.png", (303, 888, 1090, 432)),
    ("crop_master_schedule.png", "screenshot_master_schedule.png", (281, 338, 1134, 598)),
]
POSTER_FORECAST_PNG = "poster_forecast_chart_3x.png"
POSTER_MASTER_PNG = "poster_master_schedule_3x.png"

POSTER_PAGE_PT = (48 * 72, 36 * 72)
MIN_SCREENSHOT_DPI = 150

CHART_W, CHART_H = 1200, 420


def make_crops() -> None:
    for out_name, src_name, (x, y, w, h) in CROPS:
        with Image.open(os.path.join(IMAGES_DIR, src_name)) as src:
            src.crop((x, y, x + w, y + h)).save(os.path.join(IMAGES_DIR, out_name))


def chart_svg() -> str:
    right = CHART_W - 40
    label_x = 370
    bar_x, bar_h = label_x + 20, 44
    bar_max = right - bar_x - 180
    scale = bar_max / max(seats for _, seats, *_ in UNSEATED)
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
    for i, (label, seats, overflowed, color, _) in enumerate(UNSEATED):
        cy = 160 + 80 * i
        is_ours = i == len(UNSEATED) - 1
        bar_w = round(seats * scale)
        parts += [
            f'<text x="{label_x}" y="{cy + 7}" text-anchor="end" font-size="20" font-weight="600" '
            f'fill="{"#047857" if is_ours else "#334155"}">{label}</text>',
            f'<rect x="{bar_x}" y="{cy - bar_h // 2}" width="{bar_w}" height="{bar_h}" rx="6" '
            f'fill="{color if is_ours else "#94a3b8"}"/>',
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


def poster_unseated_svg() -> str:
    w, h = 680, 212
    label_x = 190
    bar_x = 200
    bar_max = 265
    scale = bar_max / PRIOR_TERM_SEATS
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="162px" '
        'style="display:block;flex-shrink:0;" '
        'font-family="-apple-system, BlinkMacSystemFont, \'Helvetica Neue\', Arial, sans-serif">',
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="8" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>',
    ]
    for tick in (0, 100, 200, 300):
        tx = bar_x + round(tick * scale)
        parts.append(
            f'<line x1="{tx}" y1="12" x2="{tx}" y2="178" stroke="#cbd5e1" stroke-width="1.2" stroke-dasharray="3,3"/>'
        )
        parts.append(
            f'<text x="{tx}" y="198" text-anchor="middle" font-size="12" font-weight="700" fill="#64748b">{tick} seats</text>'
        )
    for i, (label, seats, overflowed, color, bg_tint) in enumerate(UNSEATED):
        cy = 38 + i * 54
        is_ours = i == len(UNSEATED) - 1
        bw = max(16, round(seats * scale))
        if is_ours:
            parts.append(
                f'<rect x="8" y="{cy - 22}" width="{w - 16}" height="44" rx="6" fill="{bg_tint}" stroke="#6ee7b7" stroke-width="1.5"/>'
            )
        parts.append(
            f'<text x="{label_x}" y="{cy + 5}" text-anchor="end" font-size="14.5" '
            f'font-weight="{"800" if is_ours else "700"}" fill="{"#047857" if is_ours else "#334155"}">{label}</text>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{cy - 15}" width="{bw}" height="30" rx="5" fill="{color}"/>'
        )
        val_x = bar_x + bw + 10
        parts.append(
            f'<text x="{val_x}" y="{cy + 5.5}" font-size="16" font-weight="800" fill="{"#047857" if is_ours else "#0f172a"}">'
            f'{seats} seats'
            f'<tspan dx="6" font-size="13" font-weight="600" fill="{"#047857" if is_ours else "#475569"}">'
            f'({overflowed} courses over)</tspan></text>'
        )
    parts.append(
        '<text x="16" y="198" font-size="11.5" font-weight="700" fill="#64748b">'
        'Axis: Unseated students</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def architecture_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 510 352" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style="display:block;flex:1;min-height:0;margin:0 auto;" font-family="-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569"/>
    </marker>
    <marker id="arr-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#047857"/>
    </marker>
  </defs>

  <rect x="2" y="2" width="506" height="50" rx="7" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.4"/>
  <rect x="2" y="2" width="8" height="50" rx="4" fill="#1e3a8a"/>
  <rect x="388" y="7" width="110" height="16" rx="4" fill="#e0e7ff"/>
  <text x="443" y="18" text-anchor="middle" font-size="8.6" font-weight="800" fill="#1e3a8a">STAGE 1 · CORPUS</text>
  <text x="18" y="21" font-size="12" font-weight="800" fill="#0f172a">UIUC Freedom of Information Act (FOIA) Registrar Data</text>
  <text x="18" y="40" font-size="10.4" font-weight="500" fill="#334155">22,991 sections &#8594; 800 course-terms &#183; 40 STEM courses &#183; 19 terms (Fall 2016 to Fall 2025)</text>

  <line x1="138" y1="52" x2="138" y2="68" stroke="#475569" stroke-width="2" marker-end="url(#arr)"/>
  <text x="150" y="63.5" font-size="9.8" font-weight="700" fill="#475569">19-term enrollment trajectory per course</text>

  <rect x="2" y="70" width="506" height="50" rx="7" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.4"/>
  <rect x="2" y="70" width="8" height="50" rx="4" fill="#2563eb"/>
  <rect x="368" y="75" width="130" height="16" rx="4" fill="#dbeafe"/>
  <text x="433" y="86" text-anchor="middle" font-size="8.6" font-weight="800" fill="#1d4ed8">STAGE 2 · TOURNAMENT</text>
  <text x="18" y="89" font-size="12.2" font-weight="800" fill="#1e3a8a">Rolling-Origin Forecast Model Tournament</text>
  <text x="18" y="108" font-size="10.2" font-weight="500" fill="#334155">Seasonal Naive, Damped Trend, Pooled Ridge &#183; 15 origins pick lowest mean absolute error (MAE)</text>

  <line x1="138" y1="120" x2="138" y2="136" stroke="#047857" stroke-width="2.2" marker-end="url(#arr-green)"/>
  <text x="150" y="131.5" font-size="9.8" font-weight="700" fill="#047857">600 out-of-sample backtest residuals + point forecasts</text>

  <rect x="2" y="138" width="506" height="54" rx="7" fill="#ecfdf5" stroke="#10b981" stroke-width="1.8"/>
  <rect x="2" y="138" width="8" height="54" rx="4" fill="#047857"/>
  <rect x="336" y="144" width="162" height="16.5" rx="4" fill="#047857"/>
  <text x="417" y="155" text-anchor="middle" font-size="8.6" font-weight="800" fill="#ffffff">CORE CONTRIBUTION · STAGE 3</text>
  <text x="18" y="158" font-size="12.4" font-weight="800" fill="#065f46">Split Conformal Interval Calibration</text>
  <text x="18" y="178" font-size="10.4" font-weight="600" fill="#047857">Distribution-free per-course 80% &amp; 95% upper bounds (34/40 &amp; 39/40 empirical coverage)</text>

  <line x1="138" y1="192" x2="138" y2="208" stroke="#047857" stroke-width="2.2" marker-end="url(#arr-green)"/>
  <rect x="148" y="193" width="202" height="14.5" rx="4" fill="#d1fae5"/>
  <text x="249" y="203.5" text-anchor="middle" font-size="9.6" font-weight="800" fill="#065f46">Calibrated 80% Upper Demand Bound</text>

  <rect x="2" y="210" width="506" height="72" rx="7" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.4"/>
  <rect x="2" y="210" width="8" height="72" rx="4" fill="#0f2a5c"/>
  <rect x="358" y="215" width="140" height="16" rx="4" fill="#e2e8f0"/>
  <text x="428" y="226" text-anchor="middle" font-size="8.6" font-weight="800" fill="#0f2a5c">STAGE 4 · OR-TOOLS CP-SAT</text>
  <text x="18" y="229" font-size="12.2" font-weight="800" fill="#0f172a">Integer Programming Course &amp; Room Scheduler</text>
  <rect x="18" y="237" width="235" height="39" rx="5" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.1"/>
  <text x="26" y="251" font-size="9.4" font-weight="800" fill="#b91c1c">HARD CONSTRAINTS (0 VIOLATIONS)</text>
  <text x="26" y="267" font-size="9.5" font-weight="500" fill="#334155">Room cap &#8805; 80% bound &#183; 0 overlaps &#183; load limits</text>
  <rect x="261" y="237" width="237" height="39" rx="5" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.1"/>
  <text x="269" y="251" font-size="9.4" font-weight="800" fill="#1d4ed8">SOFT OBJECTIVE (PENALTY MINIMIZATION)</text>
  <text x="269" y="267" font-size="9.5" font-weight="500" fill="#334155">3-tier prefs: 40% Day, 40% Slot, 20% Room</text>

  <line x1="138" y1="282" x2="138" y2="298" stroke="#475569" stroke-width="2" marker-end="url(#arr)"/>
  <text x="150" y="293.5" font-size="9.8" font-weight="700" fill="#475569">Conflict-free master schedule + solver telemetry</text>

  <rect x="2" y="300" width="506" height="48" rx="7" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.4"/>
  <rect x="2" y="300" width="8" height="48" rx="4" fill="#0369a1"/>
  <rect x="368" y="305" width="130" height="16" rx="4" fill="#e0f2fe"/>
  <text x="433" y="316" text-anchor="middle" font-size="8.6" font-weight="800" fill="#0369a1">STAGE 5 · APPLICATION</text>
  <text x="18" y="319" font-size="12.2" font-weight="800" fill="#0f172a">Coordinator Workspace &amp; What-If Simulator</text>
  <text x="18" y="337" font-size="10.3" font-weight="500" fill="#334155">FastAPI + React + TypeScript &#183; Interactive master schedule &amp; counterfactual dry runs</text>
</svg>"""


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
<title>OptiSched Hack-A-Roo 2026 Academic Poster</title>
<style>
  @page { size: 48in 36in; margin: 0; }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  :root {
    --navy-dark: #071936;
    --navy: #0f2a5c;
    --navy-mid: #1e3a8a;
    --gold: #f59e0b;
    --gold-light: #fbbf24;
    --canvas: #e2e8f0;
    --ink: #0f172a;
    --body: #334155;
    --muted: #64748b;
    --line: #cbd5e1;
    --green: #047857;
    --green-mid: #059669;
    --green-bg: #ecfdf5;
    --green-line: #6ee7b7;
    --amber: #b45309;
    --amber-bg: #fffbeb;
    --amber-line: #fcd34d;
    --red: #b91c1c;
    --red-bg: #fef2f2;
    --blue: #1d4ed8;
    --blue-bg: #eff6ff;
  }
  html, body {
    width: 100%;
    height: 100%;
    background: var(--canvas);
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    color: var(--body);
    font-size: 9.5px;
    line-height: 1.28;
  }
  .page {
    zoom: 4;
    width: 1152px;
    height: 864px;
    padding: 12px 15px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: var(--canvas);
  }
  strong { color: var(--ink); }

  .banner {
    background: linear-gradient(135deg, #071936 0%, #0f2a5c 58%, #163a7a 100%);
    color: #ffffff;
    border-radius: 8px;
    border-bottom: 3.5px solid var(--gold);
    padding: 7px 12px 7px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(7, 25, 54, 0.14);
  }
  .banner-left { flex: 1; min-width: 0; }
  .eyebrow {
    display: inline-block;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--gold-light);
    background: rgba(245, 158, 11, 0.16);
    border: 1px solid rgba(251, 191, 36, 0.45);
    border-radius: 99px;
    padding: 1px 8px;
    margin-bottom: 2px;
  }
  .banner h1 {
    font-size: 17.8px;
    font-weight: 800;
    letter-spacing: -0.015em;
    line-height: 1.12;
    color: #ffffff;
    white-space: nowrap;
  }
  .banner .sub {
    font-size: 10.6px;
    font-weight: 500;
    color: #dbeafe;
    margin-top: 2px;
    white-space: nowrap;
  }
  .banner .authors {
    font-size: 9.4px;
    color: #cbd5e1;
    margin-top: 3px;
    font-weight: 600;
    white-space: nowrap;
  }
  .banner .authors b { color: #ffffff; }
  .banner .authors .sep { color: var(--gold-light); margin: 0 6px; }
  .qr-card {
    background: #ffffff;
    color: var(--ink);
    border-radius: 6px;
    padding: 4px 8px 4px 5px;
    display: flex;
    align-items: center;
    gap: 7px;
    border: 1.5px solid var(--gold);
    flex-shrink: 0;
  }
  .qr-card img {
    width: 46px;
    height: 46px;
    display: block;
    image-rendering: pixelated;
  }
  .qr-meta {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .qr-meta .qr-tag {
    font-size: 7.4px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--navy);
  }
  .qr-meta .qr-title {
    font-size: 9.4px;
    font-weight: 800;
    color: var(--ink);
  }
  .qr-meta .qr-url {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 7.5px;
    color: var(--blue);
    font-weight: 700;
  }

  .hero {
    display: grid;
    grid-template-columns: 1.24fr 1fr 1.04fr 1.04fr;
    gap: 7px;
    flex-shrink: 0;
  }
  .stat {
    background: #ffffff;
    border: 1px solid var(--line);
    border-left: 4.5px solid var(--navy);
    border-radius: 7px;
    padding: 5.5px 10px;
    display: flex;
    align-items: center;
    gap: 9px;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
  }
  .stat .n {
    font-size: 22.5px;
    font-weight: 800;
    color: var(--navy);
    letter-spacing: -0.02em;
    line-height: 1;
    white-space: nowrap;
  }
  .stat .t {
    font-size: 10.2px;
    font-weight: 800;
    color: var(--ink);
    line-height: 1.15;
    white-space: nowrap;
  }
  .stat .d {
    font-size: 8.7px;
    color: var(--muted);
    line-height: 1.2;
    margin-top: 1.5px;
  }
  .stat.lead {
    background: linear-gradient(90deg, #ecfdf5 0%, #ffffff 95%);
    border-color: var(--green-line);
    border-left: 4.5px solid var(--green);
  }
  .stat.lead .n { color: var(--green); font-size: 24.5px; }
  .stat.blue { border-left-color: var(--blue); }
  .stat.blue .n { color: var(--blue); }
  .stat.teal { border-left-color: #0369a1; }
  .stat.teal .n { color: #0369a1; }
  .stat.gold { border-left-color: var(--amber); }
  .stat.gold .n { color: var(--amber); }

  .cols {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(0, 32fr) minmax(0, 36fr) minmax(0, 32fr);
    gap: 8px;
  }
  .col {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-height: 0;
    min-width: 0;
  }
  .panel {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 7px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
    min-width: 0;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
  }
  .grow { flex: 1; }
  .panel-head {
    background: linear-gradient(90deg, #0f2a5c 0%, #1e3a8a 100%);
    color: #ffffff;
    padding: 4.5px 8.5px;
    border-bottom: 2px solid var(--gold);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 5px;
    flex-shrink: 0;
    white-space: nowrap;
  }
  .panel-head-left {
    display: flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
  }
  .panel-num {
    background: var(--gold);
    color: #071936;
    font-size: 8px;
    font-weight: 800;
    padding: 1px 4.5px;
    border-radius: 3px;
    letter-spacing: 0.03em;
  }
  .panel-title {
    font-size: 9.2px;
    font-weight: 800;
    letter-spacing: 0.025em;
    text-transform: uppercase;
    color: #ffffff;
  }
  .panel-badge {
    font-size: 7.4px;
    font-weight: 700;
    color: #dbeafe;
    background: rgba(255, 255, 255, 0.14);
    padding: 1px 5px;
    border-radius: 99px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .panel-body {
    padding: 6.5px 8.5px 7px;
    display: flex;
    flex-direction: column;
    gap: 5.5px;
    flex: 1;
    min-height: 0;
  }

  .diff-callout {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 3.5px solid var(--blue);
    border-radius: 5px;
    padding: 4.5px 7.5px;
    font-size: 8.7px;
    color: var(--ink);
    line-height: 1.25;
  }

  .sub-label {
    font-size: 8.3px;
    font-weight: 800;
    color: var(--navy);
    letter-spacing: 0.03em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 2px;
    flex-shrink: 0;
    white-space: nowrap;
  }
  .sub-label span {
    font-size: 7.7px;
    font-weight: 600;
    color: var(--muted);
    text-transform: none;
    letter-spacing: 0;
  }

  table { width: 100%; border-collapse: collapse; font-size: 8.8px; flex-shrink: 0; }
  th {
    text-align: left;
    font-size: 7.2px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.015em;
    color: var(--muted);
    padding: 3px 3px;
    border-bottom: 1.5px solid var(--line);
    background: #f8fafc;
    white-space: nowrap;
  }
  td {
    padding: 3.5px 3px;
    border-bottom: 1px solid #eef2f7;
    color: var(--body);
  }
  tr:last-child td { border-bottom: none; }
  .c { text-align: center; }
  .num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  td.num { font-weight: 700; color: var(--ink); }
  th.ours, td.ours { background: var(--green-bg); }
  th.ours { color: var(--green); }
  .pill {
    display: inline-block;
    padding: 1px 4.5px;
    border-radius: 4px;
    font-size: 7.6px;
    font-weight: 800;
    white-space: nowrap;
  }
  .pill.red { background: var(--red-bg); color: var(--red); border: 1px solid #fecaca; }
  .pill.amber { background: var(--amber-bg); color: var(--amber); border: 1px solid #fde68a; }
  .pill.blue { background: var(--blue-bg); color: var(--blue); border: 1px solid #bfdbfe; }
  .pill.green { background: #d1fae5; color: var(--green); border: 1px solid #6ee7b7; }

  .scope-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 5.5px;
    flex-shrink: 0;
  }
  .scope-card {
    border-radius: 5px;
    padding: 5.5px 6px;
    font-size: 8.1px;
    line-height: 1.28;
    min-width: 0;
  }
  .scope-card.real {
    background: var(--green-bg);
    border: 1px solid var(--green-line);
    border-top: 2.5px solid var(--green);
  }
  .scope-card.sim {
    background: var(--amber-bg);
    border: 1px solid var(--amber-line);
    border-top: 2.5px solid var(--amber);
  }
  .scope-title {
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-bottom: 2.5px;
    display: block;
    white-space: nowrap;
  }
  .scope-card.real .scope-title { color: var(--green); }
  .scope-card.sim .scope-title { color: var(--amber); }
  .scope-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .scope-list li {
    position: relative;
    padding-left: 7px;
    white-space: nowrap;
  }
  .scope-list li::before {
    content: "•";
    position: absolute;
    left: 0;
    font-weight: 800;
  }
  .horizon-strip {
    background: #f1f5f9;
    border-left: 3px solid var(--navy);
    border-radius: 4px;
    padding: 4px 6.5px;
    font-size: 8.5px;
    color: var(--body);
    line-height: 1.25;
  }

  .mae-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.15fr);
    gap: 5.5px;
    flex-shrink: 0;
  }
  .mae-card {
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 5px 6.5px;
    background: #f8fafc;
    min-width: 0;
  }
  .mae-card.ours {
    background: var(--green-bg);
    border-color: var(--green-line);
  }
  .mae-top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 3px;
    white-space: nowrap;
  }
  .mae-val {
    font-size: 15px;
    font-weight: 800;
    color: var(--ink);
    line-height: 1.05;
  }
  .mae-card.ours .mae-val { color: var(--green); }
  .mae-unit {
    font-size: 7.7px;
    font-weight: 700;
    color: var(--muted);
  }
  .mae-card.ours .mae-unit { color: var(--green); }
  .mae-name {
    font-size: 8px;
    font-weight: 700;
    color: var(--body);
    margin-top: 2px;
    white-space: nowrap;
  }
  .mae-bar-bg {
    height: 4.5px;
    background: #e2e8f0;
    border-radius: 99px;
    margin-top: 3.5px;
    overflow: hidden;
  }
  .mae-bar-fill {
    height: 100%;
    border-radius: 99px;
    background: #64748b;
  }
  .mae-card.ours .mae-bar-fill { background: var(--green-mid); }

  .cov-strip {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 5.5px;
    flex-shrink: 0;
  }
  .cov-pill-box {
    background: #f8fafc;
    border: 1px solid var(--line);
    border-radius: 5px;
    padding: 4px 7px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 8.2px;
    white-space: nowrap;
  }
  .cov-pill-box b { color: var(--navy); font-size: 8.5px; }

  .insight-callout {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 3.5px solid var(--blue);
    border-radius: 5px;
    padding: 5px 7.5px;
    font-size: 8.9px;
    color: var(--ink);
    line-height: 1.28;
    flex-shrink: 0;
  }

  .impact-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5.5px;
    flex: 1;
    min-height: 0;
  }
  .impact-card {
    background: #f8fafc;
    border: 1px solid var(--line);
    border-left: 3.5px solid var(--navy);
    border-radius: 5px;
    padding: 5px 6.5px;
    font-size: 8.3px;
    line-height: 1.25;
  }
  .impact-card.students {
    border-left-color: var(--green);
    background: linear-gradient(90deg, #ecfdf5 0%, #f8fafc 100%);
  }
  .impact-card.faculty {
    border-left-color: var(--blue);
    background: linear-gradient(90deg, #eff6ff 0%, #f8fafc 100%);
  }
  .impact-card b {
    display: block;
    font-size: 8.9px;
    color: var(--ink);
    margin-bottom: 2px;
  }

  .app-win {
    border: 1px solid #94a3b8;
    border-radius: 6px;
    overflow: hidden;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
    flex-shrink: 0;
  }
  .app-bar {
    background: #1e293b;
    color: #f8fafc;
    padding: 3.5px 7.5px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 7.8px;
    font-weight: 700;
    white-space: nowrap;
  }
  .app-dots {
    display: flex;
    align-items: center;
    gap: 3.5px;
    min-width: 0;
  }
  .dot {
    width: 5.5px;
    height: 5.5px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }
  .dot.r { background: #ef4444; }
  .dot.y { background: #f59e0b; }
  .dot.g { background: #10b981; }
  .app-title {
    color: #e2e8f0;
    font-weight: 700;
    margin-left: 4px;
  }
  .app-tag {
    font-size: 7px;
    font-weight: 800;
    padding: 0.5px 5px;
    border-radius: 3px;
    background: rgba(16, 185, 129, 0.22);
    color: #6ee7b7;
    letter-spacing: 0.03em;
    flex-shrink: 0;
  }
  .app-win img {
    display: block;
    width: 100%;
  }
  .app-cap {
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
    padding: 4px 7.5px;
    font-size: 8.5px;
    color: var(--body);
    line-height: 1.24;
  }

  .whatif-list {
    display: flex;
    flex-direction: column;
    gap: 5px;
    flex: 1;
    justify-content: space-between;
  }
  .whatif-card {
    border: 1px solid var(--line);
    border-left: 3.5px solid var(--green);
    border-radius: 5px;
    padding: 5px 7px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .whatif-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    white-space: nowrap;
  }
  .whatif-name {
    font-size: 7.7px;
    font-weight: 800;
    color: var(--ink);
  }
  .whatif-desc {
    font-size: 8.5px;
    color: var(--body);
    line-height: 1.24;
  }
  .whatif-pill {
    display: inline-block;
    padding: 1px 3.5px;
    border-radius: 4px;
    font-size: 6.3px;
    font-weight: 800;
    background: #d1fae5;
    color: var(--green);
    border: 1px solid #6ee7b7;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .footer-bar {
    background: #0f2a5c;
    color: #e2e8f0;
    border-radius: 6px;
    padding: 4px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 7.7px;
    gap: 12px;
    border-top: 2px solid var(--gold);
    flex-shrink: 0;
    white-space: nowrap;
  }
  .footer-bar b { color: var(--gold-light); }
  .footer-bar code {
    font-family: "SF Mono", Menlo, monospace;
    font-size: 7.4px;
    background: rgba(255, 255, 255, 0.14);
    color: #ffffff;
    padding: 1px 4.5px;
    border-radius: 3px;
  }
</style>
</head>
<body>
<div class="page">
  <div class="banner">
    <div class="banner-left">
      <div class="eyebrow">UMKC School of Science &amp; Engineering &middot; Hack-A-Roo 2026</div>
      <h1>OptiSched: Uncertainty-Aware Enrollment Forecasting with CP-SAT Course Scheduling</h1>
      <div class="sub">Calibrating Per-Course Conformal Demand Bounds from 19 Historical Registrar Terms to Reduce Week-One Seat Shortages</div>
      <div class="authors">
        <b>Joe Doan &middot; Tony Nguyen &middot; Tina Nguyen &middot; Salvatore Nigro</b>
        <span class="sep">|</span>
        Faculty Advisor: <b>Prof. Yugyung Lee</b>
        <span class="sep">|</span>
        Department of Computer Science &amp; Electrical Engineering
      </div>
    </div>
    <div class="qr-card">
      <img src="{{IMG_QR}}" alt="GitHub Repository QR Code" />
      <div class="qr-meta">
        <span class="qr-tag">Open-Source Benchmark</span>
        <span class="qr-title">Code &amp; FOIA Replay</span>
        <span class="qr-url">{{REPO_URL}}</span>
      </div>
    </div>
  </div>

  <div class="hero">
    <div class="stat lead">
      <div class="n">&#8722;{{REDUCTION}}%</div>
      <div>
        <div class="t">Unseated Student Seats</div>
        <div class="d">{{POINT}} &#8594; {{OURS}} seats vs. point forecast &middot; &#8722;{{REDUCTION_PRIOR}}% vs. prior ({{PRIOR}} &#8594; {{OURS}})</div>
      </div>
    </div>
    <div class="stat blue">
      <div class="n">2 / 40</div>
      <div>
        <div class="t">Courses Over Room Capacity</div>
        <div class="d">Down from 9 courses with point forecast and 8 with prior-term copy</div>
      </div>
    </div>
    <div class="stat teal">
      <div class="n">34 / 40</div>
      <div>
        <div class="t">Held-Out Courses Inside 80% Bound</div>
        <div class="d">85.0% empirical coverage &middot; 39 / 40 (97.5%) inside 95% interval</div>
      </div>
    </div>
    <div class="stat gold">
      <div class="n">3 / 3</div>
      <div>
        <div class="t">Counterfactual What-If Re-Solves</div>
        <div class="d">Best possible schedule found, 0 room or instructor conflicts</div>
      </div>
    </div>
  </div>

  <div class="cols">
    <div class="col">
      <div class="panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="panel-num">01</span>
            <span class="panel-title">Problem &amp; How OptiSched Differs</span>
          </div>
          <span class="panel-badge">19/40 Short</span>
        </div>
        <div class="panel-body">
          <p>University classrooms are assigned months before registration opens. When actual enrollment exceeds room capacity, students face week-one seat shortages and departments must relocate sections. On held-out Spring 2026 (<strong>40 STEM courses</strong>), a point forecast under-predicted <strong>19 of 40 courses</strong>.</p>
          <div class="diff-callout">
            <strong>How OptiSched Differs:</strong> Existing academic schedulers size rooms from prior-term headcount or a single point forecast. OptiSched combines per-course calibrated uncertainty bounds with a constraint programming solver (<strong>CP-SAT</strong>), cutting unseated student seats by <strong>61%</strong> vs. point forecasts (153 &#8594; 60) and <strong>82%</strong> vs. prior-term copy (338 &#8594; 60).
          </div>
          <table>
            <thead>
              <tr>
                <th>vs. Typical Approaches</th>
                <th class="c">Prior Term</th>
                <th class="c">Point</th>
                <th class="c ours">OptiSched</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Training history</strong></td>
                <td class="c"><span class="pill red">1 term</span></td>
                <td class="c"><span class="pill blue">19 terms</span></td>
                <td class="c ours"><span class="pill green">19 terms</span></td>
              </tr>
              <tr>
                <td><strong>Demand intervals</strong></td>
                <td class="c"><span class="pill red">None</span></td>
                <td class="c"><span class="pill red">None</span></td>
                <td class="c ours"><span class="pill green">80% &amp; 95%</span></td>
              </tr>
              <tr>
                <td><strong>Room buffer rule</strong></td>
                <td class="c"><span class="pill amber">Flat +5%</span></td>
                <td class="c"><span class="pill amber">Flat +5%</span></td>
                <td class="c ours"><span class="pill green">80% bound</span></td>
              </tr>
              <tr>
                <td><strong>Faculty preferences</strong></td>
                <td class="c"><span class="pill red">Manual edits</span></td>
                <td class="c"><span class="pill red">Manual edits</span></td>
                <td class="c ours"><span class="pill green">3-tier (84% match)</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="panel grow">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="panel-num">02</span>
            <span class="panel-title">End-to-End System Architecture</span>
          </div>
          <span class="panel-badge">5-Stage Pipeline</span>
        </div>
        <div class="panel-body" style="padding: 3.5px 6px;">
          {{ARCH_SVG}}
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="panel-num">03</span>
            <span class="panel-title">Data Scope: Real vs. Simulated</span>
          </div>
          <span class="panel-badge">FOIA Replay</span>
        </div>
        <div class="panel-body">
          <div class="scope-grid">
            <div class="scope-card real">
              <span class="scope-title">Real UIUC Registrar Data</span>
              <ul class="scope-list">
                <li><strong>40 STEM courses</strong> (22,991 sections)</li>
                <li><strong>19 training terms</strong> (2016 to 2025)</li>
                <li><strong>Spring 2026</strong> held-out actuals</li>
                <li><strong>Historical slot prefs</strong> (25 courses)</li>
              </ul>
            </div>
            <div class="scope-card sim">
              <span class="scope-title">Simulated Scheduling Pool</span>
              <ul class="scope-list">
                <li><strong>16-room pool</strong> (68 to 322 seats)</li>
                <li><strong>3-tier prefs</strong> (Day/Slot/Room)</li>
                <li><strong>3 What-If shocks</strong> (surge/buyout)</li>
                <li>Evaluates solver room packing</li>
              </ul>
            </div>
          </div>
          <div class="horizon-strip">
            <strong>Forecasting Horizon:</strong> 19 historical terms (ten academic years) train the models to predict <strong>one semester ahead</strong> (Spring 2026), not ten years out.
          </div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel grow">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="panel-num">04</span>
            <span class="panel-title">Empirical Results on Held-Out Spring 2026</span>
          </div>
          <span class="panel-badge">40 STEM Courses</span>
        </div>
        <div class="panel-body" style="gap: 6px;">
          <div class="sub-label">
            A. Unseated Student Seats &amp; Overflows
            <span>Lower is better &middot; Baselines sized at +5%</span>
          </div>
          {{UNSEATED_SVG}}

          <div class="sub-label">
            B. Point Forecast Mean Absolute Error (MAE)
            <span>Conformal coverage (40 courses)</span>
          </div>
          <div class="mae-grid">
            <div class="mae-card">
              <div class="mae-top"><span class="mae-val">28.25</span><span class="mae-unit">MAE (seats)</span></div>
              <div class="mae-name">Copy Prior Term (1-term)</div>
              <div class="mae-bar-bg"><div class="mae-bar-fill" style="width: 100%"></div></div>
            </div>
            <div class="mae-card">
              <div class="mae-top"><span class="mae-val">18.03</span><span class="mae-unit">&#8722;36% vs. prior</span></div>
              <div class="mae-name">Seasonal Naive</div>
              <div class="mae-bar-bg"><div class="mae-bar-fill" style="width: 63.8%"></div></div>
            </div>
            <div class="mae-card ours">
              <div class="mae-top"><span class="mae-val">17.24</span><span class="mae-unit">&#8722;39% vs. prior</span></div>
              <div class="mae-name">Pooled Ridge (&#8722;4% vs. naive)</div>
              <div class="mae-bar-bg"><div class="mae-bar-fill" style="width: 61.0%"></div></div>
            </div>
          </div>
          <div class="cov-strip">
            <div class="cov-pill-box">
              <span><b>80% Bound:</b> 34 / 40</span>
              <span class="pill green">85.0% Coverage</span>
            </div>
            <div class="cov-pill-box">
              <span><b>95% Bound:</b> 39 / 40</span>
              <span class="pill blue">97.5% Coverage</span>
            </div>
          </div>
          <div class="insight-callout">
            <strong>Key Finding:</strong> Pooled Ridge reduces point MAE by 4% over Seasonal Naive (18.03 &#8594; 17.24 seats), yet point forecasts alone still under-predict 19 of 40 courses. Sizing rooms to the <strong>calibrated 80% conformal upper bound</strong> drives the 61% reduction in unseated students.
          </div>

          <div class="sub-label">
            C. Schedule Quality vs. Actual UIUC Registrar
            <span>Held-out Spring 2026</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Schedule Metric</th>
                <th class="num ours">OptiSched</th>
                <th class="num">Actual UIUC</th>
                <th>Operational Takeaway</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Seat utilization</strong> (enrolled / cap)</td>
                <td class="num ours">64.9%</td>
                <td class="num">64.5%</td>
                <td>Matches registrar efficiency (+0.4 pp)</td>
              </tr>
              <tr>
                <td><strong>Empty-seat waste</strong> (unused cap)</td>
                <td class="num ours"><span class="pill green">35.1%</span></td>
                <td class="num">36.6%</td>
                <td>1.5 pp less wasted classroom capacity</td>
              </tr>
              <tr>
                <td><strong>Midday 10am to 2pm share</strong></td>
                <td class="num ours"><span class="pill green">22.5%</span></td>
                <td class="num">47.9%</td>
                <td>Spreads peak midday classroom load</td>
              </tr>
              <tr>
                <td><strong>Faculty preference match</strong></td>
                <td class="num ours"><span class="pill green">84.0% (21/25)</span></td>
                <td class="num">n/a</td>
                <td>3-tier score (40% Day, 40% Slot, 20% Room)</td>
              </tr>
            </tbody>
          </table>

          <div class="sub-label">
            D. Operational Impact by Stakeholder
            <span>Students &middot; Faculty &middot; Administrators</span>
          </div>
          <div class="impact-grid">
            <div class="impact-card students">
              <b>For Students</b>
              Cuts week-one unseated seats from 153 to 60 across 40 STEM courses, preventing registration lockouts in high-variance classes.
            </div>
            <div class="impact-card faculty">
              <b>For Faculty</b>
              Honors 3-tier preferences (40% Day, 40% Slot, 20% Room), matching 84.0% (21/25) of preferred teaching slots with 0 time conflicts.
            </div>
            <div class="impact-card">
              <b>For Administrators</b>
              Reduces overflowed courses from 9 to 2 without over-allocating large halls, keeping 64.9% utilization across the 16-room pool.
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="panel-num">05</span>
            <span class="panel-title">Live Application Demonstration</span>
          </div>
          <span class="panel-badge">FastAPI + React UI</span>
        </div>
        <div class="panel-body" style="gap: 6px; flex: 0 0 auto;">
          <div class="app-win">
            <div class="app-bar">
              <div class="app-dots">
                <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
                <span class="app-title">STAT 400 Demand Forecast &amp; Conformal Bounds</span>
              </div>
              <span class="app-tag">FALL 2026</span>
            </div>
            <img src="{{IMG_FORECAST}}" alt="Demand Forecast Screenshot" />
            <div class="app-cap">
              <strong>Forward Projection:</strong> Historical trajectory (2016 to 2026) and Fall 2026 forecast for STAT 400 with 188-seat point forecast, 80% interval (122 to 254), and 95% interval (57 to 319).
            </div>
          </div>

          <div class="app-win">
            <div class="app-bar">
              <div class="app-dots">
                <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
                <span class="app-title">CP-SAT Master Schedule (40 STEM Sections)</span>
              </div>
              <span class="app-tag">0 CONFLICTS</span>
            </div>
            <img src="{{IMG_MASTER}}" alt="Master Schedule Screenshot" />
            <div class="app-cap">
              <strong>Generated Master Schedule:</strong> First 7 of 40 scheduled STEM sections showing assigned classroom, capacity sized to the 80% demand bound, time slot, and instructor.
            </div>
          </div>
        </div>
      </div>

      <div class="panel grow">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="panel-num">06</span>
            <span class="panel-title">What-If Disruption Benchmarks</span>
          </div>
          <span class="panel-badge">Dry-Run Re-Solves</span>
        </div>
        <div class="panel-body">
          <div class="whatif-list">
            <div class="whatif-card">
              <div class="whatif-head">
                <span class="whatif-name">1. Demand Surge (CS +20%, STAT +15%)</span>
                <span class="whatif-pill">Best possible schedule found, 0 conflicts</span>
              </div>
              <div class="whatif-desc">CS 425 relocates to a larger lecture hall to absorb the enrollment surge; 39 of 40 sections remain in their assigned room and time slot.</div>
            </div>
            <div class="whatif-card">
              <div class="whatif-head">
                <span class="whatif-name">2. Instructor Unavailable (Grant Buyout)</span>
                <span class="whatif-pill">Best possible schedule found, 0 conflicts</span>
              </div>
              <div class="whatif-desc">Only STAT 420 is reassigned to a qualified colleague; zero cascading room or time shifts across the other 39 courses.</div>
            </div>
            <div class="whatif-card">
              <div class="whatif-head">
                <span class="whatif-name">3. Room Capacity Reduced (&times;0.9 Shock)</span>
                <span class="whatif-pill">Best possible schedule found, 0 conflicts</span>
              </div>
              <div class="whatif-desc">Up to 2 sections move to compatible classrooms to absorb the 10% capacity reduction; 38 of 40 sections stay unchanged.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer-bar">
    <div>
      <b>Reproduce:</b> <code>pytest backend/tests/test_uiuc_foia_replay.py</code>
    </div>
    <div>
      <b>Stack:</b> FastAPI &middot; OR-Tools CP-SAT &middot; React + TypeScript &middot; <b>353 Automated Tests</b> (196 backend + 157 frontend)
    </div>
    <div>
      <b>Extension:</b> Faculty Commercialization Advisor (26-field UM-16C drafter + 425-passage BM25)
    </div>
  </div>
</div>
</body>
</html>
"""


def data_uri(png_name: str) -> str:
    with open(os.path.join(IMAGES_DIR, png_name), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")


def poster_html() -> str:
    return (
        POSTER_HTML.replace("{{UNSEATED_SVG}}", poster_unseated_svg())
        .replace("{{ARCH_SVG}}", architecture_svg())
        .replace("{{REDUCTION}}", str(REDUCTION_VS_POINT_PCT))
        .replace("{{REDUCTION_PRIOR}}", str(REDUCTION_VS_PRIOR_PCT))
        .replace("{{PRIOR}}", str(PRIOR_TERM_SEATS))
        .replace("{{POINT}}", str(POINT_FORECAST_SEATS))
        .replace("{{OURS}}", str(OPTISCHED_SEATS))
        .replace("{{IMG_MASTER}}", data_uri(POSTER_MASTER_PNG))
        .replace("{{IMG_FORECAST}}", data_uri(POSTER_FORECAST_PNG))
        .replace("{{IMG_QR}}", data_uri("repo_qr.png"))
        .replace("{{REPO_URL}}", REPO_URL)
    )


def check_poster(pdf_path: str) -> None:
    doc = fitz.open(pdf_path)
    assert doc.page_count == 1, f"Expected 1-page poster, got {doc.page_count}"
    page = doc[0]
    size = (page.rect.width, page.rect.height)
    assert all(abs(got - want) <= 1 for got, want in zip(size, POSTER_PAGE_PT)), (
        f"Expected {POSTER_PAGE_PT} pt (48x36 in), got {size}"
    )
    names_by_size = {}
    for name in (POSTER_FORECAST_PNG, POSTER_MASTER_PNG, "repo_qr.png"):
        with Image.open(os.path.join(IMAGES_DIR, name)) as im:
            names_by_size[im.size] = name
    printed = {}
    for xref, _, width, height, *_ in page.get_images(full=True):
        name = names_by_size[(width, height)]
        for rect in page.get_image_rects(xref):
            printed[name] = width / (rect.width / 72)
            print(f"{name}: {width}px over {rect.width / 72:.2f} in = {printed[name]:.0f} dpi")
    for name in (POSTER_FORECAST_PNG, POSTER_MASTER_PNG):
        assert printed.get(name, 0) >= MIN_SCREENSHOT_DPI, f"{name} prints at {printed.get(name)} dpi"
    print(f"Poster PDF: 1 page, {size[0] / 72:.2f} x {size[1] / 72:.2f} in")


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

    check_poster(poster_pdf_path)
    print("Generated crops, chart PNG and 48x36 in poster PDF successfully.")


if __name__ == "__main__":
    main()
