import os
import subprocess
from pypdf import PdfReader

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IMAGES_DIR = os.path.join(REPO_ROOT, "docs", "images")
HACKATHON_DIR = os.path.join(REPO_ROOT, "docs", "hackathon")
import tempfile
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(HACKATHON_DIR, exist_ok=True)

COMPARISON_CHART_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1100px;
    height: 540px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #ffffff;
    color: #0f172a;
    padding: 28px 34px;
  }
  .card {
    border: 2px solid #cbd5e1;
    border-radius: 16px;
    padding: 24px 28px;
    background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 14px;
  }
  .title {
    font-size: 21px;
    font-weight: 800;
    color: #0f172a;
  }
  .subtitle {
    font-size: 13px;
    color: #475569;
    margin-top: 4px;
  }
  .badge {
    background: #dcfce7;
    color: #166534;
    border: 1.5px solid #86efac;
    font-weight: 800;
    font-size: 14px;
    padding: 8px 14px;
    border-radius: 999px;
  }
  .grid {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 28px;
    margin: 18px 0;
    align-items: center;
  }
  .bar-group {
    margin-bottom: 18px;
  }
  .bar-group:last-child {
    margin-bottom: 0;
  }
  .bar-label-row {
    display: flex;
    justify-content: space-between;
    font-size: 13.5px;
    font-weight: 700;
    margin-bottom: 6px;
  }
  .bar-track {
    width: 100%;
    height: 36px;
    background: #f1f5f9;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    position: relative;
  }
  .bar-fill {
    height: 100%;
    display: flex;
    align-items: center;
    padding-left: 12px;
    font-size: 13px;
    font-weight: 800;
    color: #ffffff;
    border-radius: 7px;
  }
  .fill-red { background: linear-gradient(90deg, #dc2626, #ef4444); width: 100%; }
  .fill-amber { background: linear-gradient(90deg, #d97706, #f59e0b); width: 84.9%; }
  .fill-green { background: linear-gradient(90deg, #059669, #10b981); width: 13.1%; min-width: 125px; }
  .impact-panel {
    background: #eff6ff;
    border: 1.5px solid #93c5fd;
    border-radius: 12px;
    padding: 18px 20px;
  }
  .impact-title {
    font-size: 14px;
    font-weight: 800;
    color: #1e3a8a;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 10px;
  }
  .impact-item {
    font-size: 12.8px;
    line-height: 1.45;
    color: #1e293b;
    margin-bottom: 10px;
  }
  .impact-item:last-child {
    margin-bottom: 0;
  }
  .footer {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #475569;
    border-top: 1px solid #e2e8f0;
    padding-top: 10px;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <div class="title">Held-Out Spring 2026 Room Sizing: Unseated Students &amp; Course Overflows</div>
        <div class="subtitle">Next-Semester Forecast Trained on 10 Years of Historical UIUC FOIA Data (19 Prior Terms &rarr; Held-Out Spring 2026, 40 STEM Courses)</div>
      </div>
      <div class="badge">&minus;84.6% Unseated Students (169 &rarr; 26)</div>
    </div>

    <div class="grid">
      <div>
        <div class="bar-group">
          <div class="bar-label-row">
            <span>1. Traditional Baseline: Copy Prior Term (Fall 2025 Headcount)</span>
            <span style="color:#dc2626;">199 Unseated Students &middot; 8 / 40 Courses Overflowed</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill fill-red">199 seats short (8 overflowed classes)</div>
          </div>
        </div>

        <div class="bar-group">
          <div class="bar-label-row">
            <span>2. Raw Point Forecast Only (Pooled Ridge Mean Estimate, MAE 17.24)</span>
            <span style="color:#d97706;">169 Unseated Students &middot; 9 / 40 Courses Overflowed</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill fill-amber">169 seats short (9 overflowed classes)</div>
          </div>
        </div>

        <div class="bar-group">
          <div class="bar-label-row">
            <span>3. OptiSched: 80% Split-Conformal Upper Bound + CP-SAT Solver</span>
            <span style="color:#059669;">26 Unseated Students &middot; Only 2 / 40 Courses Overflowed</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill fill-green">26 seats (&minus;84.6%)</div>
          </div>
        </div>
      </div>

      <div class="impact-panel">
        <div class="impact-title">Why This Matters in Practice</div>
        <div class="impact-item">
          <strong>For Students:</strong> Eliminates 143 unseated student lockouts in Week 1, preventing delayed prerequisite chains and graduation bottlenecks in high-demand STEM courses.
        </div>
        <div class="impact-item">
          <strong>For University Administrators:</strong> Cuts emergency first-week room swaps and last-minute section splits from 9 courses down to 2 while maintaining <strong>0 hard conflicts (OPTIMAL)</strong> and <strong>84.0% 2-year faculty habit continuity</strong>.
        </div>
        <div class="impact-item">
          <strong>Calibrated Coverage:</strong> Actual Spring 2026 enrollment falls inside OptiSched's 95% bound for <strong>39/40 courses (97.5%)</strong> and 80% bound for <strong>34/40 courses (85.0%)</strong>.
        </div>
      </div>
    </div>

    <div class="footer">
      <span><strong>Real Data Scope:</strong> 800 historical course-semester enrollments (Fall 2016 &ndash; Spring 2026) from 22,991 UIUC FOIA sections.</span>
      <span><strong>Simulation Scope:</strong> CP-SAT room allocation, 3-tier faculty preferences &amp; counterfactual What-If shocks.</span>
    </div>
  </div>
</body>
</html>
"""

POSTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>OptiSched Hack-A-Roo Poster &amp; Technical Brief</title>
<style>
  @page {
    size: letter landscape;
    margin: 0.22in 0.28in;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    background: #ffffff;
    font-size: 7.4pt;
    line-height: 1.22;
  }
  .banner {
    background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 60%, #1d4ed8 100%);
    color: #ffffff;
    padding: 7px 12px;
    border-radius: 7px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .banner h1 {
    font-size: 11.8pt;
    font-weight: 800;
    letter-spacing: -0.01em;
  }
  .banner .sub {
    font-size: 7.4pt;
    color: #bfdbfe;
    margin-top: 1px;
  }
  .banner .meta {
    text-align: right;
    font-size: 7.2pt;
    color: #e2e8f0;
  }
  .cols {
    display: grid;
    grid-template-columns: 1fr 1.16fr 1fr;
    gap: 8px;
  }
  .panel {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 8px;
    background: #f8fafc;
    margin-bottom: 6px;
  }
  .panel:last-child {
    margin-bottom: 0;
  }
  .panel-title {
    font-size: 7.9pt;
    font-weight: 800;
    color: #1e3a8a;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border-bottom: 1.5px solid #bfdbfe;
    padding-bottom: 2px;
    margin-bottom: 4px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7.0pt;
    margin-top: 3px;
  }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 2.2px 4px;
    text-align: left;
  }
  th {
    background: #eff6ff;
    color: #1e3a8a;
    font-weight: 700;
  }
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 5px;
    margin-bottom: 5px;
  }
  .kpi {
    background: #ffffff;
    border: 1px solid #93c5fd;
    border-left: 3px solid #2563eb;
    border-radius: 5px;
    padding: 4px 5px;
  }
  .kpi-val {
    font-size: 9.2pt;
    font-weight: 800;
    color: #0f172a;
  }
  .kpi-lbl {
    font-size: 6.4pt;
    color: #475569;
  }
  .bar-wrap {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 7px;
    margin: 4px 0;
  }
  .bar-row {
    margin-bottom: 4px;
  }
  .bar-row:last-child {
    margin-bottom: 0;
  }
  .bar-head {
    display: flex;
    justify-content: space-between;
    font-size: 7.1pt;
    font-weight: 700;
    margin-bottom: 1.5px;
  }
  .bar-bg {
    height: 13px;
    background: #f1f5f9;
    border-radius: 4px;
    overflow: hidden;
  }
  .bar-fg {
    height: 100%;
    color: #fff;
    font-size: 6.6pt;
    font-weight: 700;
    padding-left: 6px;
    display: flex;
    align-items: center;
  }
  ul {
    padding-left: 13px;
  }
  li {
    margin-bottom: 2px;
  }
  .flow-steps {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
    margin: 4px 0;
  }
  .flow-step {
    background: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 5px;
    padding: 3.5px 5px;
    font-size: 6.9pt;
  }
  .flow-step strong {
    display: block;
    color: #1e3a8a;
    font-size: 7.2pt;
  }
</style>
</head>
<body>
  <div class="banner">
    <div>
      <h1>OptiSched: Uncertainty-Aware Next-Term Enrollment Forecasting &amp; CP-SAT Academic Scheduling</h1>
      <div class="sub">Bridging 10-Year Historical Registrar Data, Split Conformal Risk Bounds, and Constraint Programming for Conflict-Free University Timetables</div>
    </div>
    <div class="meta">
      <strong>Hack-A-Roo 2026 &middot; UMKC SSE</strong><br/>
      Team: Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro<br/>
      Faculty Advisor: Prof. Yugyung Lee
    </div>
  </div>

  <div class="cols">
    <!-- Column 1 -->
    <div>
      <div class="panel">
        <div class="panel-title">1. Innovation vs. Existing Scheduling Systems</div>
        <p style="margin-bottom:3px;">Traditional university schedulers treat next-semester enrollment as a static number copied from last term, causing severe Week-1 overflows.</p>
        <table>
          <thead>
            <tr>
              <th>Capability</th>
              <th>Existing Schedulers</th>
              <th>OptiSched (Ours)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Demand Input</strong></td>
              <td>Prior-term copy or raw point estimate</td>
              <td><strong>Next-term forecast + 80%/95% Conformal Bounds</strong></td>
            </tr>
            <tr>
              <td><strong>Historical Training</strong></td>
              <td>1 prior term</td>
              <td><strong>10 years history (19 terms &rarr; next semester)</strong></td>
            </tr>
            <tr>
              <td><strong>Conflict &amp; Prefs</strong></td>
              <td>Manual edits / greedy heuristics</td>
              <td><strong>Exact OR-Tools CP-SAT + 3-Tier Faculty Prefs</strong></td>
            </tr>
            <tr>
              <td><strong>What-If Shocks</strong></td>
              <td>Manual spreadsheet trial</td>
              <td><strong>Live Counterfactual Simulator + Bottleneck Proof</strong></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <div class="panel-title">2. End-to-End System Architecture</div>
        <div class="flow-steps">
          <div class="flow-step">
            <strong>1. Historical ETL</strong>
            10-yr UIUC FOIA (22,991 sections &rarr; 800 course-terms; 19 train, 1 held-out).
          </div>
          <div class="flow-step">
            <strong>2. Forecast + Bounds</strong>
            Pooled Ridge next-term forecast + Split Conformal 80%/95% upper bounds.
          </div>
          <div class="flow-step">
            <strong>3. CP-SAT Solver</strong>
            Hard room/slot/load constraints + 3-tier faculty preferences (40/40/20).
          </div>
          <div class="flow-step">
            <strong>4. Live What-Ifs</strong>
            Enrollment surges, faculty buyouts, room closures &amp; NL Copilot.
          </div>
        </div>
        <ul>
          <li><strong>Important Clarification:</strong> The model uses <strong>10 years of historical data (Fall 2016 &ndash; Fall 2025)</strong> to predict the <strong>next semester (Spring 2026)</strong>, rather than predicting 10 years into the future.</li>
          <li><strong>3-Tier Faculty Hierarchy:</strong> Resolves per-course overrides (Tier 1), general semester availability (Tier 2), and 2-year causal teaching habits (Tier 3) across 40% Day, 40% Slot, and 20% Room weights.</li>
        </ul>
      </div>
    </div>

    <!-- Column 2 -->
    <div>
      <div class="panel">
        <div class="panel-title">3. Verified Held-Out Spring 2026 Quantitative Results</div>
        <div class="kpi-row">
          <div class="kpi">
            <div class="kpi-val">&minus;84.6%</div>
            <div class="kpi-lbl">Unseated Students (169 &rarr; 26)</div>
          </div>
          <div class="kpi">
            <div class="kpi-val">9 &rarr; 2</div>
            <div class="kpi-lbl">Overflowed Courses Cut</div>
          </div>
          <div class="kpi">
            <div class="kpi-val">97.5% / 85%</div>
            <div class="kpi-lbl">95% (39/40) &amp; 80% (34/40) Coverage</div>
          </div>
          <div class="kpi">
            <div class="kpi-val">84.0%</div>
            <div class="kpi-lbl">2-Yr Faculty Habit Match (0 Conflicts)</div>
          </div>
        </div>

        <div class="bar-wrap">
          <div style="font-size:7.4pt;font-weight:800;color:#0f172a;margin-bottom:3px;">Visual Comparison: Unseated Students on Held-Out Spring 2026 (40 Courses)</div>
          <div class="bar-row">
            <div class="bar-head">
              <span>Copy Prior Term (Fall 2025 Headcount)</span>
              <span style="color:#dc2626;">199 Unseated Students (8 Overflows)</span>
            </div>
            <div class="bar-bg"><div class="bar-fg" style="width:100%;background:#dc2626;">199 seats short</div></div>
          </div>
          <div class="bar-row">
            <div class="bar-head">
              <span>Raw Point Forecast Only (Pooled Ridge, MAE 17.24)</span>
              <span style="color:#d97706;">169 Unseated Students (9 Overflows)</span>
            </div>
            <div class="bar-bg"><div class="bar-fg" style="width:84.9%;background:#d97706;">169 seats short</div></div>
          </div>
          <div class="bar-row">
            <div class="bar-head">
              <span>OptiSched 80% Conformal Upper Bound + CP-SAT</span>
              <span style="color:#059669;">26 Unseated Students (2 Overflows, &minus;84.6%)</span>
            </div>
            <div class="bar-bg"><div class="bar-fg" style="width:18%;background:#059669;">26 seats</div></div>
          </div>
        </div>

        <ul>
          <li><strong>How This Benefits Students:</strong> Prevents 143 Week-1 seat lockouts in core STEM courses, keeping students on track for prerequisites and on-time graduation.</li>
          <li><strong>How This Benefits Administrators:</strong> Eliminates chaotic Week-1 room reassignments and emergency section splits while guaranteeing <strong>0 room or instructor double-bookings (OPTIMAL)</strong>.</li>
          <li><strong>Forecasting Accuracy:</strong> On held-out Spring 2026, Pooled Ridge reaches <strong>17.24 MAE</strong> vs <strong>18.03</strong> for Seasonal Naive and <strong>28.25</strong> for copying prior term.</li>
        </ul>
      </div>

      <div class="panel">
        <div class="panel-title">4. Live Counterfactual What-If Demonstration</div>
        <table>
          <thead>
            <tr>
              <th>Operational Shock</th>
              <th>What OptiSched Demonstrates Live</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1. Enrollment Surge</strong> (CS +20%, STAT +15%)</td>
              <td>Re-solves timetable with forecast sizing; upgrades surging classes into larger compatible halls with minimal ripple.</td>
            </tr>
            <tr>
              <td><strong>2. Instructor Unavailable</strong> (1-Course Buyout)</td>
              <td>Proves <strong>INFEASIBILITY</strong> when no coverage is allowed (20&times;2=40 cliff); finds <strong>1-course minimal move</strong> with colleague/adjunct coverage.</td>
            </tr>
            <tr>
              <td><strong>3. Classroom Reassigned</strong> (0.9x Capacity)</td>
              <td>Detects exact lab/auditorium capacity cliffs (e.g. ECE 380 exceeding 30-seat lab cap) and re-packs feasible rooms.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Column 3 -->
    <div>
      <div class="panel">
        <div class="panel-title">5. Evaluation Clarification: Real vs. Simulated</div>
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Provenance &amp; Scope</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Real Registrar Data</strong></td>
              <td>800 course-semester enrollments across 40 STEM courses &amp; 20 terms (Fall 2016 &ndash; Spring 2026) from UIUC FOIA records.</td>
            </tr>
            <tr>
              <td><strong>Simulated Scenarios</strong></td>
              <td>Campus classroom pool, 3-tier faculty preference weights, and What-If counterfactual shocks (surge, buyout, room closure).</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="panel">
        <div class="panel-title">6. Extension: Faculty Commercialization Advisor</div>
        <p style="margin-bottom:3px;">As a connected extension for faculty whose research leads to a grant course buyout:</p>
        <ul>
          <li><strong>In-Memory UM-16C Disclosure Drafter:</strong> Extracts 26 disclosure fields with verbatim quotes from uploaded research paper PDFs.</li>
          <li><strong>BM25 Policy Retrieval:</strong> Searches <strong>425 indexed passages across 7 UM System &amp; UMKC policy documents</strong> to generate a conflict-of-interest checklist.</li>
          <li><strong>Direct Scheduler Integration:</strong> Triggers the live <strong>CP-SAT Course-Release Simulator</strong> to verify department teaching coverage before approving a buyout.</li>
        </ul>
      </div>

      <div class="panel">
        <div class="panel-title">7. Reproducing the Demonstration</div>
        <p style="margin-bottom:2px;"><strong>Repo:</strong> <code>github.com/JoeDoan/CS5551_Advanced-Software-Engineering-</code></p>
        <p style="margin-bottom:2px;"><strong>1. Start Backend (FastAPI + OR-Tools CP-SAT):</strong></p>
        <pre style="background:#0f172a;color:#f8fafc;padding:3px 5px;border-radius:4px;font-size:6.6pt;margin-bottom:3px;">cd backend &amp;&amp; python3 -m uvicorn app.main:app --port 8000</pre>
        <p style="margin-bottom:2px;"><strong>2. Start Frontend (React + TypeScript + Vite):</strong></p>
        <pre style="background:#0f172a;color:#f8fafc;padding:3px 5px;border-radius:4px;font-size:6.6pt;margin-bottom:3px;">cd frontend &amp;&amp; npm run dev   # http://localhost:5173/insights</pre>
        <p style="margin-bottom:2px;"><strong>3. Run Automated Verification Suites (Backend + Frontend):</strong></p>
        <pre style="background:#0f172a;color:#f8fafc;padding:3px 5px;border-radius:4px;font-size:6.6pt;">cd backend &amp;&amp; pytest &amp;&amp; cd ../frontend &amp;&amp; npx vitest run</pre>
      </div>
    </div>
  </div>
</body>
</html>
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        chart_html_path = os.path.join(tmpdir, "comparison_chart.html")
        chart_png_path = os.path.join(IMAGES_DIR, "unseated_students_comparison.png")
        with open(chart_html_path, "w", encoding="utf-8") as fh:
            fh.write(COMPARISON_CHART_HTML)

        subprocess.run(
            [
                CHROME_BIN,
                "--headless",
                "--disable-gpu",
                "--window-size=1100,540",
                f"--screenshot={chart_png_path}",
                f"file://{chart_html_path}",
            ],
            check=True,
        )

        poster_html_path = os.path.join(tmpdir, "hackaroo_poster.html")
        with open(poster_html_path, "w", encoding="utf-8") as fh:
            fh.write(POSTER_HTML)

        poster_pdf_path = os.path.join(HACKATHON_DIR, "OptiSched_HackARoo_Poster.pdf")
        subprocess.run(
            [
                CHROME_BIN,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={poster_pdf_path}",
                f"file://{poster_html_path}",
            ],
            check=True,
        )

        reader = PdfReader(poster_pdf_path)
        assert len(reader.pages) == 1, f"Expected 1-page poster, got {len(reader.pages)}"
        print("Generated chart PNG and 1-page poster PDF successfully.")


if __name__ == "__main__":
    main()
