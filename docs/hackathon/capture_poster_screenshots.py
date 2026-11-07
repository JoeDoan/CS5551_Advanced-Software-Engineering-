import os
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
IMAGES_DIR = REPO_ROOT / "docs" / "images"
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
VIEWPORT = {"width": 1440, "height": 900}
SCALE = 3
FORECAST_COURSE = "STAT 400"
SCHEDULE_ROWS = 7
SCHEDULE_COLUMNS = 4

FORECAST_PNG = IMAGES_DIR / "poster_forecast_chart_3x.png"
MASTER_PNG = IMAGES_DIR / "poster_master_schedule_3x.png"

SCHEDULE_CLIP_JS = """([rows, cols]) => {
  const table = document.querySelector('[data-testid^="schedule-table-row-"]').closest('table');
  const cells = [
    ...Array.from(table.querySelectorAll('thead th')).slice(0, cols),
    ...Array.from(table.querySelectorAll('tbody tr')).slice(0, rows)
      .flatMap((tr) => Array.from(tr.children).slice(0, cols)),
  ];
  const rects = cells.map((c) => c.getBoundingClientRect());
  const left = Math.min(...rects.map((r) => r.left));
  const top = Math.min(...rects.map((r) => r.top));
  const right = Math.max(...rects.map((r) => r.right));
  const bottom = Math.max(...rects.map((r) => r.bottom));
  return { x: left, y: top, width: right - left, height: bottom - top };
}"""


def http_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, timeout_sec: float = 60.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if http_ready(url):
            return
        time.sleep(0.3)
    raise RuntimeError(f"Service did not become ready at {url}")


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def capture_forecast(page: Page) -> None:
    page.goto(f"{FRONTEND_URL}/insights", wait_until="networkidle")
    chart = page.locator('[data-testid="forecast-chart"]')
    chart.wait_for(state="visible", timeout=20000)
    selected = page.locator('[data-testid="forecast-course-select"] option:checked').inner_text()
    assert FORECAST_COURSE in selected, f"Default forecast course is {selected!r}, expected {FORECAST_COURSE}"
    page.wait_for_timeout(1000)
    chart.screenshot(path=str(FORECAST_PNG))


def capture_master_schedule(page: Page) -> None:
    page.goto(f"{FRONTEND_URL}/schedule", wait_until="networkidle")
    page.click('[data-testid="view-mode-table"]')
    first_row = page.locator('[data-testid^="schedule-table-row-"]').first
    first_row.wait_for(state="visible", timeout=20000)
    page.evaluate(
        """() => {
          const head = document.querySelector('[data-testid^="schedule-table-row-"]').closest('table').querySelector('thead');
          window.scrollBy(0, head.getBoundingClientRect().top - 160);
        }"""
    )
    page.mouse.move(0, 0)
    page.wait_for_timeout(500)
    clip = page.evaluate(SCHEDULE_CLIP_JS, [SCHEDULE_ROWS, SCHEDULE_COLUMNS])
    assert clip["y"] >= 0 and clip["y"] + clip["height"] <= VIEWPORT["height"], f"Clip outside viewport: {clip}"
    page.screenshot(path=str(MASTER_PNG), clip=clip)


def main() -> None:
    backend_proc = None
    frontend_proc = None
    try:
        if not http_ready(f"{BACKEND_URL}/api/v1/health"):
            backend_proc = subprocess.Popen(
                ["python3", "-m", "uvicorn", "app.main:app", "--port", "8000"],
                cwd=BACKEND_DIR,
                env={**os.environ, "DATA_PROFILE": "uiuc_foia"},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_for_url(f"{BACKEND_URL}/api/v1/health")
        if not http_ready(FRONTEND_URL):
            frontend_proc = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "5173"],
                cwd=FRONTEND_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_for_url(FRONTEND_URL)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE).new_page()
            page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
            page.click('[data-testid="demo-login-coordinator"]')
            page.wait_for_selector('a[href="/insights"]', state="visible", timeout=15000)
            capture_forecast(page)
            capture_master_schedule(page)
            browser.close()
    finally:
        stop(frontend_proc)
        stop(backend_proc)

    for path in (FORECAST_PNG, MASTER_PNG):
        print(f"Saved {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
