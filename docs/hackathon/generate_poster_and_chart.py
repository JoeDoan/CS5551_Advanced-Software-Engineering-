import base64
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

# (output name, source screenshot, (x, y, width, height) in source pixels)
CROPS = [
    ("crop_forecast.png", "screenshot_forecast_benchmark.png", (305, 440, 1090, 465)),
    ("crop_whatif_presets.png", "screenshot_whatif_simulator.png", (309, 342, 1079, 89)),
    ("crop_whatif_result.png", "screenshot_whatif_simulator.png", (303, 888, 1090, 432)),
    ("crop_master_schedule.png", "screenshot_master_schedule.png", (281, 338, 1134, 598)),
]

CHART_W, CHART_H = 1200, 420


def make_crops() -> None:
    for out_name, src_name, (x, y, w, h) in CROPS:
        with Image.open(os.path.join(IMAGES_DIR, src_name)) as src:
            src.crop((x, y, x + w, y + h)).save(os.path.join(IMAGES_DIR, out_name))


def chart_svg(width: int = CHART_W, label_x: int = 370) -> str:
    right = width - 40
    bar_x, bar_h = label_x + 20, 44
    bar_max = right - bar_x - 150
    scale = bar_max / max(seats for _, seats, _ in UNSEATED)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {CHART_H}" '
        f'width="100%" font-family="-apple-system, BlinkMacSystemFont, \'Helvetica Neue\', Arial, sans-serif">',
        f'<rect width="{width}" height="{CHART_H}" fill="#ffffff"/>',
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
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    font-size: 7.2pt;
    line-height: 1.25;
  }
  .page { width: 1008px; height: 766px; display: flex; flex-direction: column; gap: 6px; }
  .banner {
    background: #0f2a5c;
    color: #ffffff;
    border-radius: 6px;
    padding: 7px 12px 6px;
  }
  .banner .row { display: flex; justify-content: space-between; align-items: baseline; white-space: nowrap; }
  .banner h1 { font-size: 15.5pt; font-weight: 800; letter-spacing: -0.01em; }
  .banner .event { font-size: 9pt; font-weight: 700; color: #bfdbfe; }
  .banner .sub { font-size: 9pt; color: #dbeafe; margin-top: 2px; }
  .banner .byline { font-size: 8.2pt; color: #cbd5e1; }
  .cols { flex: 1; display: grid; grid-template-columns: 32fr 36fr 32fr; gap: 8px; min-height: 0; }
  .col { display: flex; flex-direction: column; gap: 6px; min-height: 0; }
  .panel {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 8px 7px;
    background: #f8fafc;
  }
  .grow { flex: 1; }
  h2 {
    font-size: 8.6pt;
    font-weight: 800;
    color: #0f2a5c;
    border-bottom: 1.5px solid #bfdbfe;
    padding-bottom: 2px;
    margin-bottom: 5px;
    white-space: nowrap;
  }
  h3 { font-size: 7.6pt; font-weight: 800; color: #0f2a5c; margin: 5px 0 2px; }
  p { margin-bottom: 3px; }
  ul, ol { padding-left: 13px; }
  li { margin-bottom: 1.5px; }
  li:last-child { margin-bottom: 0; }
  strong { color: #0f172a; }
  .shot {
    display: block;
    width: 100%;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px;
    margin-top: 5px;
  }
  .shot img { display: block; width: 100%; }
  .caption { font-size: 6.8pt; font-style: italic; color: #475569; margin-top: 3px; }
  .chart { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; overflow: hidden; }
  .chart svg { display: block; }
  .tiles { display: grid; grid-template-columns: 1fr; gap: 4px; margin: 6px 0; }
  .tile {
    display: grid;
    grid-template-columns: 66px 1fr;
    grid-template-rows: auto auto;
    align-items: center;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 3px solid #059669;
    border-radius: 4px;
    padding: 2px 6px;
    white-space: nowrap;
  }
  .tile .v { grid-row: 1 / 3; font-size: 11pt; font-weight: 800; color: #047857; }
  .tile .k { font-size: 7.6pt; font-weight: 800; color: #0f172a; }
  .tile .d { font-size: 7pt; color: #475569; }
  table { width: 100%; border-collapse: collapse; font-size: 6.9pt; background: #ffffff; }
  th, td { border: 1px solid #cbd5e1; padding: 1.5px 4px; text-align: left; vertical-align: top; }
  th { background: #eef2f7; color: #0f2a5c; font-weight: 700; white-space: nowrap; }
  td.num { white-space: nowrap; text-align: right; }
  .url { font-weight: 700; color: #0f2a5c; white-space: nowrap; font-size: 7.6pt; }
  .stack { color: #475569; font-size: 6.9pt; margin-top: 3px; }
</style>
</head>
<body>
<div class="page">
  <div class="banner">
    <div class="row">
      <h1>OptiSched: Uncertainty-Aware Enrollment Forecasting with CP-SAT Course Scheduling</h1>
    </div>
    <div class="row">
      <div class="sub">Rooms sized to calibrated next-term demand bounds and scheduled conflict-free with constraint programming</div>
    </div>
    <div class="row">
      <div class="byline">Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro &middot; Advisor: Prof. Yugyung Lee &middot; UMKC School of Science and Engineering</div>
      <span class="event">Hack-A-Roo 2026</span>
    </div>
  </div>

  <div class="cols">
    <div class="col">
      <div class="panel">
        <h2>1. Problem and Approach</h2>
        <p>Rooms are assigned before registration opens. A room sized to last term's headcount or to a single forecast leaves students without seats when demand runs high.</p>
        <p>OptiSched forecasts next-term enrollment for each course and attaches calibrated 80% and 95% prediction intervals. Each room is sized to the 80% upper bound. A CP-SAT model then assigns rooms, time slots and instructors with zero hard conflicts.</p>
        <h3>Key contributions</h3>
        <ul>
          <li>Next-term enrollment forecasts with split-conformal prediction intervals.</li>
          <li>Room sizes from the interval passed directly into a CP-SAT timetable model.</li>
          <li>Held-out evaluation on a real term: Spring 2026, 40 courses.</li>
          <li>What-If re-solves for enrollment surges, instructor release and room changes, with minimal schedule change.</li>
        </ul>
      </div>
      <div class="panel grow">
        <h2>2. System Pipeline</h2>
        <ol>
          <li><strong>Data.</strong> Public UIUC registrar records (FOIA). 22,991 sections become 800 course-term enrollments (40 courses, 20 terms).</li>
          <li><strong>Forecast.</strong> Seasonal naive, damped trend and pooled ridge models are scored by a rolling-origin backtest; the lowest-MAE model is used, with split-conformal 80% and 95% intervals.</li>
          <li><strong>Schedule.</strong> CP-SAT assigns each course a room, a slot and an instructor. Hard constraints: room capacity, room and instructor overlap, teaching load. Soft constraints: faculty day, slot and room preferences (weights 40/40/20).</li>
          <li><strong>What-If.</strong> A dry-run re-solve under a scenario. It reports metric changes and every course that moved.</li>
        </ol>
        <div class="shot"><img src="{{IMG_MASTER}}" alt="Master schedule" /></div>
        <div class="caption">Master Schedule view. 40 sections; the auditor reports 0 hard conflicts.</div>
        <div class="stack">Stack: FastAPI &middot; OR-Tools CP-SAT &middot; React + TypeScript</div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <h2>3. Data and Evaluation</h2>
        <ul>
          <li><strong>Training data:</strong> 19 terms, Fall 2016 to Fall 2025 (real). <strong>Forecast target:</strong> next term.</li>
          <li><strong>Test term:</strong> Spring 2026, held out, 40 STEM courses (real enrollment).</li>
          <li><strong>Faculty preferences:</strong> each instructor's most frequent slot over the prior 2 years (real, 25 of 40 courses).</li>
          <li><strong>Simulated:</strong> room pool (16 rooms) and What-If scenarios.</li>
          <li><strong>Baselines:</strong> copy prior term (Fall 2025) +5%, and point forecast +5%.</li>
          <li><strong>Unseated students:</strong> enrollment above the assigned room capacity, summed over courses.</li>
        </ul>
      </div>
      <div class="panel grow">
        <h2>4. Results: Held-Out Spring 2026</h2>
        <div class="chart">{{POSTER_CHART_SVG}}</div>
        <div class="tiles">
          <div class="tile"><div class="v">39%</div><div class="k">lower error than copy prior term</div><div class="d">MAE 17.24 vs 28.25; seasonal naive 18.03</div></div>
          <div class="tile"><div class="v">85%</div><div class="k">of courses inside the 80% interval</div><div class="d">34/40; 95% interval holds 39/40 (97.5%)</div></div>
          <div class="tile"><div class="v">2 of 40</div><div class="k">courses overflowed their room</div><div class="d">vs 8 (prior term) and 9 (point forecast)</div></div>
          <div class="tile"><div class="v">64.9%</div><div class="k">seat utilization</div><div class="d">vs 64.5% in the actual UIUC schedule</div></div>
        </div>
        <table>
          <thead><tr><th>Schedule quality, Spring 2026</th><th>OptiSched</th><th>Actual UIUC</th></tr></thead>
          <tbody>
            <tr><td>Empty-seat waste</td><td class="num">35.1%</td><td class="num">36.6%</td></tr>
            <tr><td>Share of classes 10am to 2pm</td><td class="num">22.5%</td><td class="num">47.9%</td></tr>
            <tr><td>Habit continuity (2-year)</td><td class="num">84% (21/25)</td><td class="num">n/a</td></tr>
            <tr><td>Hard conflicts (OPTIMAL)</td><td class="num">0</td><td class="num">n/a</td></tr>
          </tbody>
        </table>
        <p style="margin-top:5px;"><strong>Who benefits.</strong> Students face fewer first-week seat shortages. Administrators make fewer room changes after registration, with no loss in seat utilization.</p>
      </div>
      <div class="panel">
        <h2>Code and Reproduction</h2>
        <div class="url">{{REPO_URL}}</div>
        <div>Setup, demo and benchmark: see the README.</div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <h2>5. Forecast in the App</h2>
        <div class="shot" style="margin-top:0;"><img src="{{IMG_FORECAST}}" alt="Demand forecast" /></div>
        <div class="caption">Demand Forecast view. STAT 400 history with the next-term forecast and 80%/95% intervals.</div>
      </div>
      <div class="panel grow">
        <h2>6. Working Demonstration: What-If</h2>
        <p>Each preset re-solves a simulated Spring 2027 term as a dry run. Placements the scenario does not force to change stay where they are.</p>
        <div class="shot"><img src="{{IMG_PRESETS}}" alt="What-If presets" /></div>
        <div class="shot"><img src="{{IMG_RESULT}}" alt="What-If result" /></div>
        <div class="caption">What-If view, instructor-unavailable preset. Only STAT 420 moved.</div>
        <table style="margin-top:5px;">
          <thead><tr><th>Scenario and input</th><th>Output</th></tr></thead>
          <tbody>
            <tr><td><strong>Enrollment surge</strong><br/>CS +20%, STAT +15%</td><td>2 courses move to larger rooms; both solves OPTIMAL</td></tr>
            <tr><td><strong>Instructor unavailable</strong><br/>1-course grant buyout</td><td>1 course moves to a qualified colleague; both solves OPTIMAL</td></tr>
            <tr><td><strong>Room reassigned</strong><br/>All room capacities &times; 0.9</td><td>3 courses move to feasible rooms; both solves OPTIMAL</td></tr>
          </tbody>
        </table>
      </div>
      <div class="panel">
        <h2>7. Extension: Faculty Commercialization Advisor</h2>
        <p>Drafts a UM-16C invention disclosure from an uploaded paper and retrieves clauses from 425 passages in 7 UM System and UMKC policy sources. Links to the instructor-release What-If to check teaching coverage.</p>
      </div>
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
        POSTER_HTML.replace("{{POSTER_CHART_SVG}}", chart_svg(width=900, label_x=260))
        .replace("{{IMG_MASTER}}", data_uri("crop_master_schedule.png"))
        .replace("{{IMG_FORECAST}}", data_uri("crop_forecast.png"))
        .replace("{{IMG_PRESETS}}", data_uri("crop_whatif_presets.png"))
        .replace("{{IMG_RESULT}}", data_uri("crop_whatif_result.png"))
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
