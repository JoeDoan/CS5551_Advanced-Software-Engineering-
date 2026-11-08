from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import wave
from typing import Callable

import edge_tts
import imageio_ffmpeg
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
HACKATHON_DIR = ROOT / "docs" / "hackathon"
BRAIN_DIR = Path("/Users/dudoan/.gemini/antigravity/brain/9b68c356-195b-438e-ab3c-d02f2446978c")
SCRATCH_DIR = BRAIN_DIR / "scratch"
DOWNLOADS_DIR = Path("/Users/dudoan/Downloads")
AUDIO_TMP_DIR = Path("/tmp/optisched_live_demo_tts")

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
FPS = 24
VIEWPORT = {"width": 1920, "height": 1080}
VOICE = "en-US-AndrewMultilingualNeural"
VOICE_RATE = "+3%"
BEAT_PAD_SECONDS = 0.22


@dataclass(frozen=True)
class Beat:
    id: str
    section_badge: str
    badge_color: str
    caption: str
    narration: str


BEATS: tuple[Beat, ...] = (
    Beat(
        id="intro_team",
        section_badge="UMKC OptiSched · Team Intro",
        badge_color="#2563eb",
        caption="Hello everyone! We are Joe Doan, Tony Nguyen, Tina Nguyen, and Salvatore Nigro, advised by Professor Yugyung Lee and Professor Sudipta Chattopadhyay, presenting OptiSched.",
        narration=(
            "Hello everyone! We are Joe Doan, Tony Nguyen, Tina Nguyen, and Salvatore Nigro, "
            "advised by Professor Yugyung Lee and Professor Sudipta Chattopadhyay, presenting OptiSched."
        ),
    ),
    Beat(
        id="problem_and_login",
        section_badge="Problem & Coordinator Login",
        badge_color="#2563eb",
        caption="Universities assign classrooms months before registration opens, so sizing rooms to last term's headcount leaves high-demand courses overflowing.",
        narration=(
            "Universities assign classrooms months before registration opens, so sizing rooms "
            "to last term's headcount leaves high-demand courses overflowing. "
            "Let's sign in as Course Coordinator and open Insights."
        ),
    ),
    Beat(
        id="foia_training_data",
        section_badge="Stage 1 · Real UIUC FOIA Data",
        badge_color="#0284c7",
        caption="OptiSched trains on 19 terms of real University of Illinois registrar records from Fall 2016 to Fall 2025, forecasting one term ahead.",
        narration=(
            "As shown in the green badge at top right, OptiSched trains on nineteen terms of "
            "real University of Illinois registrar records from Fall 2016 to Fall 2025, "
            "forecasting one term ahead."
        ),
    ),
    Beat(
        id="ridge_and_conformal_chart",
        section_badge="Stage 1 · Conformal Intervals",
        badge_color="#0284c7",
        caption="Our champion pooled Ridge model predicts next-term enrollment and calibrates 80% and 95% split-conformal intervals on the right of the chart.",
        narration=(
            "Our champion pooled Ridge model predicts next-term enrollment and calibrates "
            "eighty percent and ninety-five percent split-conformal intervals, shown by the "
            "blue bars on the right of the chart."
        ),
    ),
    Beat(
        id="live_course_switch",
        section_badge="Stage 1 · Interactive Course Forecast",
        badge_color="#0284c7",
        caption="When we select different courses in the dropdown, the historical enrollment curve and prediction intervals update live.",
        narration=(
            "When we select different courses in the dropdown, the historical enrollment curve "
            "and prediction intervals update live."
        ),
    ),
    Beat(
        id="benchmark_stage1",
        section_badge="Spring 2026 Audit · Forecast MAE",
        badge_color="#059669",
        caption="Across 40 held-out Spring 2026 courses, Stage 1 shows pooled Ridge cuts forecast error to 17.24 seats vs 28.25 (39% reduction) with 85% and 97.5% coverage.",
        narration=(
            "Scrolling down to our held-out Spring 2026 benchmark across forty courses, "
            "Stage 1 on the left shows pooled Ridge cuts forecast error to 17.24 seats "
            "versus 28.25 for copying Fall 2025, while covering 85 and 97.5 percent of courses."
        ),
    ),
    Beat(
        id="benchmark_stage2",
        section_badge="Spring 2026 Audit · Schedule Quality",
        badge_color="#059669",
        caption="On the right, Stage 2 shows our CP-SAT schedule achieves 0 hard conflicts, matches actual UIUC seat utilization at 64.9%, and preserves 84% of faculty habits.",
        narration=(
            "On the right, Stage 2 shows our CP-SAT schedule achieves zero hard conflicts, "
            "matches actual UIUC seat utilization at 64.9 percent, and preserves 84 percent "
            "of faculty two-year teaching habits."
        ),
    ),
    Beat(
        id="unseated_comparison",
        section_badge="Key Result · −61% Unseated Students",
        badge_color="#16a34a",
        caption="Copying Fall 2025 leaves 338 students unseated and point forecasts leave 153. Sizing rooms to OptiSched's 80% conformal bound reduces unseated students to 60 (−61%).",
        narration=(
            "In the unseated student chart below, copying Fall 2025 leaves 338 students "
            "without a seat, and the point forecast leaves 153. Sizing rooms to OptiSched's "
            "eighty percent conformal bound reduces unseated students to 60, a 61 percent drop."
        ),
    ),
    Beat(
        id="data_evaluation_scope",
        section_badge="Evaluation · Real vs Simulated",
        badge_color="#0d9488",
        caption="Below the chart, the Data and Evaluation box separates real UIUC FOIA enrollment and teaching history from the simulated room pool and What-If scenarios.",
        narration=(
            "Below the chart, the Data and Evaluation box separates real UIUC FOIA enrollment "
            "and teaching history from the simulated room pool and What-If scenarios."
        ),
    ),
    Beat(
        id="master_schedule",
        section_badge="Stage 2 · Master Timetable",
        badge_color="#4f46e5",
        caption="Opening the Master Schedule, CP-SAT certifies 0 hard conflicts across all 40 sections across the Room Matrix, Weekly Calendar, and Table View.",
        narration=(
            "Opening the Master Schedule, CP-SAT certifies zero hard conflicts across all "
            "forty sections, and coordinators can switch live between the Room Matrix, "
            "Weekly Calendar, and Table View."
        ),
    ),
    Beat(
        id="whatif_preset1_surge",
        section_badge="What-If 1 · Enrollment Surge",
        badge_color="#7c3aed",
        caption="Preset 1 (+20% CS, +15% STAT): Clicking Run Simulation re-solves live and moves only over-capacity sections into larger rooms.",
        narration=(
            "Now let's test three live disruptions in the What-If Simulator. First, an "
            "enrollment surge with Computer Science up 20 percent and Statistics up 15 percent. "
            "Clicking Run Simulation re-solves live and moves only over-capacity sections into larger rooms."
        ),
    ),
    Beat(
        id="whatif_preset2_buyout",
        section_badge="What-If 2 · Instructor Unavailable",
        badge_color="#9333ea",
        caption="Preset 2 (NSF Grant Course Release): Running the solver assigns a qualified colleague in the same department to cover STAT 420, moving just 1 course.",
        narration=(
            "Second, an instructor becomes unavailable for an NSF grant course release. "
            "Clicking Preset 2 and running the solver assigns a qualified colleague in the "
            "same department to cover STAT 420, moving just one course."
        ),
    ),
    Beat(
        id="whatif_preset3_room",
        section_badge="What-If 3 · Room Reassigned (0.9x)",
        badge_color="#c026d3",
        caption="Preset 3 (0.9x Room Capacity): Running the solver relocates only the courses that exceed the reduced room limits while keeping all other placements unchanged.",
        narration=(
            "Third, a classroom reassignment scales room capacities down to 0.9 times baseline. "
            "Running the solver relocates only the courses that exceed the reduced room limits "
            "while keeping all other placements unchanged."
        ),
    ),
    Beat(
        id="commercialization_and_close",
        section_badge="Extension · UM-16C Disclosure",
        badge_color="#d97706",
        caption="The Commercialization Advisor drafts a UM-16C invention disclosure from a paper abstract. OptiSched connects conformal demand intervals to CP-SAT optimization.",
        narration=(
            "Finally, as an extension for faculty commercializing research, the Commercialization "
            "Advisor drafts a UM-16C invention disclosure from a paper abstract. By connecting "
            "calibrated demand intervals to CP-SAT optimization, OptiSched sizes rooms for "
            "likely student demand. Thank you!"
        ),
    ),
)

OVERLAY_INIT_JS = """
(() => {
  window.__optischedEnsureOverlay = () => {
    let root = document.getElementById('optisched-demo-overlay-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'optisched-demo-overlay-root';
      root.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483645;overflow:hidden;';

      const teamBanner = document.createElement('div');
      teamBanner.id = 'demo-team-banner';
      teamBanner.style.cssText = [
        'position:fixed',
        'top:18px',
        'left:50%',
        'transform:translateX(-50%)',
        'z-index:2147483646',
        'background:rgba(15, 23, 42, 0.94)',
        'color:#ffffff',
        'border:2px solid rgba(56, 189, 248, 0.72)',
        'border-radius:14px',
        'padding:12px 24px',
        'box-shadow:0 14px 34px rgba(0, 0, 0, 0.5)',
        'font-family:Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        'font-size:14.5px',
        'font-weight:700',
        'letter-spacing:0.01em',
        'white-space:nowrap',
        'opacity:0',
        'transition:opacity 0.18s ease',
        'pointer-events:none'
      ].join(';');
      teamBanner.textContent = 'UMKC Hack-A-Roo · OptiSched Team: Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro · Advisors: Prof. Yugyung Lee & Prof. Sudipta Chattopadhyay';

      const ring = document.createElement('div');
      ring.id = 'demo-target-ring';
      ring.style.cssText = [
        'position:fixed',
        'left:0',
        'top:0',
        'width:0',
        'height:0',
        'opacity:0',
        'pointer-events:none',
        'border:2.5px solid rgba(37, 99, 235, 0.82)',
        'background:rgba(59, 130, 246, 0.07)',
        'border-radius:12px',
        'box-shadow:0 0 0 4px rgba(59, 130, 246, 0.18)',
        'transition:opacity 0.12s ease',
        'z-index:2147483645'
      ].join(';');

      const ripple = document.createElement('div');
      ripple.id = 'demo-ripple';
      ripple.style.cssText = [
        'position:fixed',
        'left:0',
        'top:0',
        'width:0',
        'height:0',
        'opacity:0',
        'pointer-events:none',
        'border-radius:9999px',
        'border:3px solid #2563eb',
        'background:rgba(59, 130, 246, 0.24)',
        'box-shadow:0 0 18px rgba(37, 99, 235, 0.55)',
        'transform:translate(-50%, -50%)',
        'z-index:2147483646'
      ].join(';');

      const captionBar = document.createElement('div');
      captionBar.id = 'demo-caption-bar';
      captionBar.style.cssText = [
        'position:fixed',
        'bottom:22px',
        'left:50%',
        'transform:translateX(-50%)',
        'z-index:2147483646',
        'max-width:1460px',
        'width:88%',
        'background:rgba(15, 23, 42, 0.95)',
        'color:#ffffff',
        'border:2px solid rgba(56, 189, 248, 0.55)',
        'border-radius:16px',
        'padding:14px 24px',
        'box-shadow:0 16px 38px rgba(0, 0, 0, 0.55)',
        'font-family:Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        'display:flex',
        'align-items:center',
        'gap:16px',
        'pointer-events:none'
      ].join(';');

      const badge = document.createElement('span');
      badge.id = 'demo-caption-badge';
      badge.style.cssText = [
        'background:#2563eb',
        'color:#ffffff',
        'font-size:12px',
        'font-weight:800',
        'text-transform:uppercase',
        'letter-spacing:0.06em',
        'padding:6px 14px',
        'border-radius:999px',
        'white-space:nowrap',
        'flex-shrink:0',
        'box-shadow:0 2px 10px rgba(37, 99, 235, 0.4)'
      ].join(';');

      const text = document.createElement('span');
      text.id = 'demo-caption-text';
      text.style.cssText = [
        'font-size:18px',
        'line-height:1.42',
        'font-weight:600',
        'color:#ffffff',
        'text-shadow:0 1px 2px rgba(0, 0, 0, 0.8)',
        'letter-spacing:-0.01em'
      ].join(';');

      captionBar.appendChild(badge);
      captionBar.appendChild(text);

      const cursor = document.createElement('div');
      cursor.id = 'demo-cursor';
      cursor.style.cssText = [
        'position:fixed',
        'left:0',
        'top:0',
        'width:36px',
        'height:36px',
        'pointer-events:none',
        'z-index:2147483647',
        'filter:drop-shadow(0 4px 10px rgba(15, 23, 42, 0.48))'
      ].join(';');
      cursor.innerHTML = `
        <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="5" cy="5" r="4.5" fill="rgba(59, 130, 246, 0.42)" />
          <path d="M4.5 3.5L14.2 30.2L18.4 19.6L29.2 15.6L4.5 3.5Z"
                fill="#0f172a"
                stroke="#ffffff"
                stroke-width="2.4"
                stroke-linejoin="round" />
          <circle cx="5.2" cy="4.2" r="2.2" fill="#38bdf8" />
        </svg>
      `;

      root.appendChild(teamBanner);
      root.appendChild(ring);
      root.appendChild(ripple);
      root.appendChild(captionBar);
      root.appendChild(cursor);
      (document.body || document.documentElement).appendChild(root);
    }
    return root;
  };

  window.__optischedUpdateOverlay = (state) => {
    window.__optischedEnsureOverlay();
    const teamBanner = document.getElementById('demo-team-banner');
    const cursor = document.getElementById('demo-cursor');
    const ripple = document.getElementById('demo-ripple');
    const ring = document.getElementById('demo-target-ring');
    const badge = document.getElementById('demo-caption-badge');
    const text = document.getElementById('demo-caption-text');

    if (teamBanner) {
      teamBanner.style.opacity = state.showTeamBanner ? '1' : '0';
    }
    if (cursor) {
      cursor.style.transform = `translate3d(${state.x - 4.5}px, ${state.y - 3.5}px, 0) scale(${state.cursorScale || 1})`;
    }
    if (badge && state.badgeText) {
      badge.textContent = state.badgeText;
      badge.style.background = state.badgeColor || '#2563eb';
    }
    if (text && state.captionText !== undefined) {
      text.textContent = state.captionText;
    }
    if (ripple) {
      if (state.rippleActive) {
        ripple.style.left = `${state.rippleX}px`;
        ripple.style.top = `${state.rippleY}px`;
        ripple.style.width = `${state.rippleDiameter}px`;
        ripple.style.height = `${state.rippleDiameter}px`;
        ripple.style.opacity = `${state.rippleOpacity}`;
      } else {
        ripple.style.opacity = '0';
      }
    }
    if (ring) {
      if (state.ringRect && state.ringRect.width > 0 && state.ringRect.height > 0) {
        const pad = 5;
        ring.style.left = `${state.ringRect.left - pad}px`;
        ring.style.top = `${state.ringRect.top - pad}px`;
        ring.style.width = `${state.ringRect.width + pad * 2}px`;
        ring.style.height = `${state.ringRect.height + pad * 2}px`;
        ring.style.opacity = '1';
      } else {
        ring.style.opacity = '0';
      }
    }
  };
})();
"""


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - pow(-2.0 * t + 2.0, 3) / 2.0


def http_ready(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def wait_for_url(url: str, timeout_sec: float = 45.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if http_ready(url):
            return
        time.sleep(0.3)
    raise RuntimeError(f"Service did not become ready at {url}")


def warmup_backend() -> None:
    with urllib.request.urlopen(f"{BACKEND_URL}/api/v1/health", timeout=15.0) as resp:
        resp.read()

    login_payload = json.dumps(
        {"identifier": "coordinator@umkc.edu", "password": "coordinator123"}
    ).encode("utf-8")
    login_req = urllib.request.Request(
        f"{BACKEND_URL}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(login_req, timeout=15.0) as resp:
        token = json.loads(resp.read().decode("utf-8"))["access_token"]

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    for path in (
        "/api/v1/forecast/enrollment",
        "/api/v1/forecast/empirical-benchmark",
    ):
        req = urllib.request.Request(
            f"{BACKEND_URL}{path}", headers=auth_headers, method="GET"
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            resp.read()

    for use_fc in (True, False):
        payload = json.dumps(
            {
                "semester_id": 6,
                "use_forecast": use_fc,
                "enrollment_growth": [],
                "room_capacity_scale": 1.0,
                "buyouts": [],
                "coverage_strategy": "overload",
                "blocked_room_slots": [],
                "change_policy": "minimal",
                "time_limit_seconds": 10,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_URL}/api/v1/scenarios/simulate",
            data=payload,
            headers=auth_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            resp.read()


async def _synthesize_beat_mp3(text: str, out_mp3: Path) -> None:
    eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    eleven_voice = os.getenv("ELEVENLABS_VOICE_ID", "n2rbvE306nIxtmgEocS6").strip()
    if eleven_key:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{eleven_voice}",
            data=json.dumps(
                {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.55, "similarity_boost": 0.80},
                }
            ).encode("utf-8"),
            headers={
                "xi-api-key": eleven_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45.0) as resp:
            out_mp3.write_bytes(resp.read())
        return

    for attempt in range(5):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE)
            await communicate.save(str(out_mp3))
            if out_mp3.exists() and out_mp3.stat().st_size > 1000:
                return
        except Exception:
            if attempt == 4:
                raise
            await asyncio.sleep(0.8 * (attempt + 1))


def generate_voiceover_and_durations(
    ffmpeg_exe: str,
) -> tuple[Path, list[float]]:
    import hashlib

    AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)
    durations: list[float] = []
    padded_wavs: list[Path] = []
    eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    eleven_voice = os.getenv("ELEVENLABS_VOICE_ID", "n2rbvE306nIxtmgEocS6").strip()
    voice_tag = f"elevenlabs:{eleven_voice}" if eleven_key else f"{VOICE}|{VOICE_RATE}"

    for idx, beat in enumerate(BEATS):
        digest = hashlib.sha256(
            f"{voice_tag}|{BEAT_PAD_SECONDS}|{beat.narration}".encode("utf-8")
        ).hexdigest()[:12]
        mp3_path = AUDIO_TMP_DIR / f"cue_{idx:02d}_{beat.id}_{digest}.mp3"
        wav_path = AUDIO_TMP_DIR / f"cue_{idx:02d}_{beat.id}_{digest}_atempo114.wav"
        if not mp3_path.exists():
            asyncio.run(_synthesize_beat_mp3(beat.narration, mp3_path))
        if not wav_path.exists():
            subprocess.run(
                [
                    ffmpeg_exe,
                    "-y",
                    "-i",
                    str(mp3_path),
                    "-af",
                    f"atempo=1.14,apad=pad_dur={BEAT_PAD_SECONDS}",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-c:a",
                    "pcm_s16le",
                    str(wav_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            dur = frames / float(rate)
        durations.append(dur)
        padded_wavs.append(wav_path)
        print(f"  Cue {idx + 1:02d} ({beat.id}): {dur:.2f}s")

    total_dur = sum(durations)
    print(f"Total voiceover duration across {len(BEATS)} cues: {total_dur:.2f}s")
    if not (115.0 <= total_dur <= 180.0):
        raise RuntimeError(f"Total audio duration {total_dur:.2f}s outside [115, 180]s target window")

    master_wav = AUDIO_TMP_DIR / "optisched_live_demo_audio.wav"
    with wave.open(str(master_wav), "wb") as out_wf:
        for idx, wav_path in enumerate(padded_wavs):
            with wave.open(str(wav_path), "rb") as in_wf:
                if idx == 0:
                    out_wf.setparams(in_wf.getparams())
                out_wf.writeframes(in_wf.readframes(in_wf.getnframes()))

    return master_wav, durations


class LiveRecorder:
    def __init__(self, page: Page, ffmpeg_proc: subprocess.Popen[bytes]) -> None:
        self.page = page
        self.ffmpeg_proc = ffmpeg_proc
        self.x = 960.0
        self.y = 540.0
        self.badge_text = BEATS[0].section_badge
        self.badge_color = BEATS[0].badge_color
        self.caption_text = BEATS[0].caption
        self.caption_spans: list[tuple[int, int, str]] = []
        self.show_team_banner = False
        self.ring_rect: dict[str, float] | None = None
        self.ripple_active = False
        self.ripple_x = 0.0
        self.ripple_y = 0.0
        self.ripple_diameter = 0.0
        self.ripple_opacity = 0.0
        self.cursor_scale = 1.0
        self.frames_emitted = 0

    def set_beat_caption(self, beat: Beat, start_frame: int = 0, end_frame: int = 0) -> None:
        import re

        self.badge_text = beat.section_badge
        self.badge_color = beat.badge_color
        self.show_team_banner = beat.id == "intro_team"
        parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", beat.narration.strip()) if s.strip()]
        if len(parts) == 2 and len(parts[0]) <= 20:
            parts = [f"{parts[0]} {parts[1]}"]
        total_chars = max(1, sum(len(s) for s in parts))
        total_frames = max(1, end_frame - start_frame)
        spans: list[tuple[int, int, str]] = []
        cur_f = start_frame
        for i, sent in enumerate(parts):
            next_f = end_frame if i == len(parts) - 1 else cur_f + round(total_frames * len(sent) / total_chars)
            spans.append((cur_f, max(cur_f + 1, next_f), sent))
            cur_f = next_f
        self.caption_spans = spans
        self.caption_text = parts[0] if parts else beat.caption

    def emit_frame(self) -> None:
        for sf, ef, sent in self.caption_spans:
            if sf <= self.frames_emitted <= ef:
                self.caption_text = sent
                break
        state = {
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "badgeText": self.badge_text,
            "badgeColor": self.badge_color,
            "captionText": self.caption_text,
            "showTeamBanner": self.show_team_banner,
            "ringRect": self.ring_rect,
            "rippleActive": self.ripple_active,
            "rippleX": round(self.ripple_x, 1),
            "rippleY": round(self.ripple_y, 1),
            "rippleDiameter": round(self.ripple_diameter, 1),
            "rippleOpacity": round(self.ripple_opacity, 3),
            "cursorScale": round(self.cursor_scale, 3),
        }
        try:
            self.page.evaluate("s => window.__optischedUpdateOverlay && window.__optischedUpdateOverlay(s)", state)
        except Exception:
            self.page.evaluate(OVERLAY_INIT_JS)
            self.page.evaluate("s => window.__optischedUpdateOverlay(s)", state)

        jpg_bytes = self.page.screenshot(type="jpeg", quality=92)
        assert self.ffmpeg_proc.stdin is not None
        self.ffmpeg_proc.stdin.write(jpg_bytes)
        self.frames_emitted += 1

    def hold(self, seconds: float) -> None:
        count = max(1, round(seconds * FPS))
        self.hold_frames(count)

    def hold_frames(self, count: int) -> None:
        for i in range(max(0, count)):
            self.x += math.sin((self.frames_emitted + i) * 0.18) * 0.25
            self.y += math.cos((self.frames_emitted + i) * 0.15) * 0.2
            self.emit_frame()

    def _query_rect(self, selector: str) -> dict[str, float] | None:
        return self.page.evaluate(
            """sel => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { left: r.left, top: r.top, width: r.width, height: r.height, bottom: r.bottom, right: r.right };
            }""",
            selector,
        )

    def scroll_to_y(self, target_y: float, duration: float = 0.65) -> None:
        start_y = float(self.page.evaluate("() => window.scrollY"))
        max_scroll = float(
            self.page.evaluate("() => Math.max(0, document.documentElement.scrollHeight - window.innerHeight)")
        )
        clamped_y = max(0.0, min(target_y, max_scroll))
        if abs(clamped_y - start_y) < 6.0:
            return
        self.ring_rect = None
        steps = max(4, round(duration * FPS))
        for i in range(1, steps + 1):
            t = ease_in_out_cubic(i / steps)
            cur_y = start_y + (clamped_y - start_y) * t
            self.page.evaluate("y => window.scrollTo(0, y)", cur_y)
            self.emit_frame()

    def ensure_in_viewport(self, selector: str, top_margin: float = 110.0) -> None:
        rect = self._query_rect(selector)
        if not rect:
            return
        if rect["top"] < 55.0 or rect["bottom"] > 945.0:
            cur_scroll = float(self.page.evaluate("() => window.scrollY"))
            desired_scroll = cur_scroll + rect["top"] - top_margin
            self.scroll_to_y(desired_scroll, duration=0.55)

    def move_to_coords(
        self,
        target_x: float,
        target_y: float,
        duration: float = 0.55,
        ring_rect: dict[str, float] | None = None,
    ) -> None:
        start_x, start_y = self.x, self.y
        steps = max(3, round(duration * FPS))
        arc = min(28.0, math.hypot(target_x - start_x, target_y - start_y) * 0.08)
        for i in range(1, steps + 1):
            raw_t = i / steps
            t = ease_in_out_cubic(raw_t)
            arc_offset = math.sin(raw_t * math.pi) * arc
            self.x = start_x + (target_x - start_x) * t
            self.y = start_y + (target_y - start_y) * t - arc_offset * 0.35
            if i >= steps - 2:
                self.ring_rect = ring_rect
            self.emit_frame()
        self.x, self.y = target_x, target_y
        self.ring_rect = ring_rect

    def move_to(
        self,
        selector: str,
        duration: float = 0.55,
        rx: float = 0.5,
        ry: float = 0.5,
        highlight: bool = True,
        auto_scroll: bool = True,
    ) -> dict[str, float] | None:
        self.page.wait_for_selector(selector, state="visible", timeout=15000)
        if auto_scroll:
            self.ensure_in_viewport(selector)
        rect = self._query_rect(selector)
        if not rect:
            return None
        tx = max(16.0, min(1904.0, rect["left"] + rect["width"] * rx))
        ty = max(16.0, min(965.0, rect["top"] + rect["height"] * ry))
        ring = rect if (highlight and rect["height"] <= 460.0) else None
        self.move_to_coords(tx, ty, duration=duration, ring_rect=ring)
        return rect

    def click(
        self,
        selector: str | None = None,
        duration: float = 0.5,
        rx: float = 0.5,
        ry: float = 0.5,
        highlight: bool = True,
    ) -> None:
        if selector is not None:
            self.move_to(selector, duration=duration, rx=rx, ry=ry, highlight=highlight)
        click_x, click_y = self.x, self.y
        self.page.mouse.move(click_x, click_y)
        self.page.mouse.down()
        self.cursor_scale = 0.86
        self.ripple_active = True
        self.ripple_x = click_x
        self.ripple_y = click_y
        self.ripple_diameter = 16.0
        self.ripple_opacity = 0.95
        self.emit_frame()
        self.page.mouse.up()

        ripple_frames = 10
        for i in range(1, ripple_frames + 1):
            p = i / ripple_frames
            self.cursor_scale = 0.86 + 0.14 * p
            self.ripple_diameter = 16.0 + 96.0 * ease_in_out_cubic(p)
            self.ripple_opacity = max(0.0, 0.92 * (1.0 - p))
            if selector is not None:
                rect = self._query_rect(selector)
                if rect and highlight and rect["height"] <= 460.0:
                    self.ring_rect = rect
                else:
                    self.ring_rect = None
            self.emit_frame()

        self.cursor_scale = 1.0
        self.ripple_active = False

    def pad_until_frame(self, target_frame: int) -> None:
        remaining = target_frame - self.frames_emitted
        if remaining > 0:
            self.hold_frames(remaining)


def cue_01_intro_team(rec: LiveRecorder) -> None:
    rec.page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
    rec.page.evaluate(OVERLAY_INIT_JS)
    rec.show_team_banner = True
    rec.hold(0.5)
    rec.move_to("#demo-team-banner", duration=0.65, rx=0.5, ry=0.5, highlight=True, auto_scroll=False)
    rec.hold(2.2)
    rec.move_to("h1", duration=0.65, rx=0.5, ry=0.5, highlight=True, auto_scroll=False)
    rec.hold(1.5)
    rec.move_to("h2", duration=0.6, rx=0.45, ry=0.5, highlight=True, auto_scroll=False)


def cue_02_problem_and_login(rec: LiveRecorder) -> None:
    rec.show_team_banner = False
    rec.hold(2.5)
    rec.move_to('[data-testid="demo-login-coordinator"]', duration=0.8, rx=0.45, ry=0.5, auto_scroll=False)
    rec.hold(1.2)
    rec.click('[data-testid="demo-login-coordinator"]', duration=0.25, rx=0.45, ry=0.5)
    rec.page.wait_for_selector('a[href="/insights"]', state="visible", timeout=15000)
    rec.ring_rect = None
    rec.hold(1.2)
    rec.click('a[href="/insights"]', duration=0.8, rx=0.5, ry=0.5)
    rec.page.wait_for_selector('[data-testid="forecast-panel"]', state="visible", timeout=20000)
    rec.page.wait_for_selector('[data-testid="empirical-benchmark-card"]', state="visible", timeout=20000)
    rec.move_to('[data-testid="real-data-badge"]', duration=0.55, rx=0.5, ry=0.5, highlight=True, auto_scroll=False)


def cue_03_foia_training_data(rec: LiveRecorder) -> None:
    rec.scroll_to_y(0, duration=0.3)
    rec.move_to('[data-testid="real-data-badge"]', duration=0.55, rx=0.5, ry=0.5, highlight=True, auto_scroll=False)
    rec.hold(4.2)
    rec.move_to('[data-testid="forecast-horizon-note"]', duration=0.75, rx=0.35, ry=0.5, highlight=True, auto_scroll=False)


def cue_04_ridge_and_conformal_chart(rec: LiveRecorder) -> None:
    rec.move_to('[data-testid="champion-badge"]', duration=0.65, rx=0.5, ry=0.5, highlight=True, auto_scroll=False)
    rec.hold(2.2)
    chart_rect = rec.move_to('[data-testid="forecast-chart"]', duration=0.65, rx=0.18, ry=0.58, highlight=True, auto_scroll=False)
    if chart_rect:
        rec.move_to_coords(
            chart_rect["left"] + chart_rect["width"] * 0.56,
            chart_rect["top"] + chart_rect["height"] * 0.48,
            duration=1.2,
            ring_rect=chart_rect,
        )
        rec.hold(0.6)
        rec.move_to_coords(
            chart_rect["left"] + chart_rect["width"] * 0.94,
            chart_rect["top"] + chart_rect["height"] * 0.36,
            duration=1.0,
            ring_rect=chart_rect,
        )


def cue_05_live_course_switch(rec: LiveRecorder) -> None:
    rec.click('[data-testid="forecast-course-select"]', duration=0.55, rx=0.45, ry=0.5)
    rec.page.locator('[data-testid="forecast-course-select"]').select_option(index=1)
    rec.hold(1.4)
    rec.click('[data-testid="forecast-course-select"]', duration=0.4, rx=0.45, ry=0.5)
    rec.page.locator('[data-testid="forecast-course-select"]').select_option(index=2)
    rec.hold(0.6)
    rec.move_to('[data-testid="forecast-summary"]', duration=0.55, rx=0.35, ry=0.4, highlight=True, auto_scroll=False)


def cue_06_benchmark_stage1(rec: LiveRecorder) -> None:
    card_rect = rec._query_rect('[data-testid="empirical-benchmark-card"]')
    if card_rect:
        cur_scroll = float(rec.page.evaluate("() => window.scrollY"))
        rec.scroll_to_y(cur_scroll + card_rect["top"] - 28.0, duration=0.8)

    stage1 = rec.move_to('[data-testid="benchmark-stage1"]', duration=0.75, rx=0.28, ry=0.38, auto_scroll=False)
    rec.hold(3.8)
    if stage1:
        rec.move_to_coords(
            stage1["left"] + stage1["width"] * 0.72,
            stage1["top"] + stage1["height"] * 0.38,
            duration=0.75,
            ring_rect=stage1,
        )
        rec.hold(3.2)
        rec.move_to_coords(
            stage1["left"] + stage1["width"] * 0.65,
            stage1["top"] + stage1["height"] * 0.78,
            duration=0.75,
            ring_rect=stage1,
        )


def cue_07_benchmark_stage2(rec: LiveRecorder) -> None:
    stage2 = rec.move_to('[data-testid="benchmark-stage2"]', duration=0.75, rx=0.72, ry=0.18, auto_scroll=False)
    rec.hold(3.0)
    if stage2:
        rec.move_to_coords(
            stage2["left"] + stage2["width"] * 0.75,
            stage2["top"] + stage2["height"] * 0.42,
            duration=0.75,
            ring_rect=stage2,
        )
        rec.hold(3.0)
        rec.move_to_coords(
            stage2["left"] + stage2["width"] * 0.75,
            stage2["top"] + stage2["height"] * 0.88,
            duration=0.75,
            ring_rect=stage2,
        )


def cue_08_unseated_comparison(rec: LiveRecorder) -> None:
    chart_rect = rec._query_rect('[data-testid="unseated-comparison-chart"]')
    if chart_rect:
        cur_scroll = float(rec.page.evaluate("() => window.scrollY"))
        rec.scroll_to_y(cur_scroll + chart_rect["top"] - 70.0, duration=0.75)

    u_rect = rec.move_to(
        '[data-testid="unseated-comparison-chart"]', duration=0.75, rx=0.72, ry=0.32, auto_scroll=False
    )
    rec.hold(3.2)
    if u_rect:
        rec.move_to_coords(
            u_rect["left"] + u_rect["width"] * 0.72,
            u_rect["top"] + u_rect["height"] * 0.50,
            duration=0.7,
            ring_rect=u_rect,
        )
        rec.hold(2.8)
        rec.move_to_coords(
            u_rect["left"] + u_rect["width"] * 0.72,
            u_rect["top"] + u_rect["height"] * 0.68,
            duration=0.7,
            ring_rect=u_rect,
        )
        rec.hold(2.8)
        rec.move_to_coords(
            u_rect["left"] + u_rect["width"] * 0.80,
            u_rect["top"] + u_rect["height"] * 0.15,
            duration=0.65,
            ring_rect=u_rect,
        )


def cue_09_data_evaluation_scope(rec: LiveRecorder) -> None:
    rec.move_to('[data-testid="evaluation-scope-callout"]', duration=0.75, rx=0.45, ry=0.5, auto_scroll=False)
    rec.hold(4.0)
    rec.move_to('[data-testid="benchmark-selected-course"]', duration=0.75, rx=0.5, ry=0.5, auto_scroll=True)


def cue_10_master_schedule(rec: LiveRecorder) -> None:
    rec.scroll_to_y(0, duration=0.5)
    rec.click('a[href="/schedule"]', duration=0.65, rx=0.5, ry=0.5)
    rec.page.wait_for_selector('[data-testid="schedule-section-count"]', state="visible", timeout=15000)
    rec.page.wait_for_function(
        """() => {
            const el = document.querySelector('[data-testid="schedule-section-count"]');
            return el && !el.textContent.includes('0 of 0');
        }""",
        timeout=15000,
    )
    rec.move_to('[data-testid="conflict-inspector-panel"]', duration=0.6, rx=0.62, ry=0.5)
    rec.hold(1.5)
    rec.click('[data-testid="view-mode-matrix"]', duration=0.6, rx=0.5, ry=0.5)
    rec.hold(1.2)
    rec.click('[data-testid="view-mode-calendar"]', duration=0.6, rx=0.5, ry=0.5)
    rec.hold(1.2)
    rec.click('[data-testid="view-mode-table"]', duration=0.6, rx=0.5, ry=0.5)


def _run_simulation_and_wait(rec: LiveRecorder, check_js: str) -> None:
    rec.click('[data-testid="run-scenario"]', duration=0.65, rx=0.5, ry=0.5)
    for _ in range(14):
        if bool(rec.page.evaluate(check_js)):
            break
        rec.emit_frame()
    rec.page.wait_for_function(check_js, timeout=45000)
    rec.hold(0.3)


def cue_11_whatif_preset1_surge(rec: LiveRecorder) -> None:
    rec.scroll_to_y(0, duration=0.4)
    rec.click('a[href="/insights"]', duration=0.7, rx=0.5, ry=0.5)
    rec.page.wait_for_selector('[data-testid="tab-whatif"]', state="visible", timeout=15000)
    rec.click('[data-testid="tab-whatif"]', duration=0.65, rx=0.5, ry=0.5)
    rec.page.wait_for_selector('[data-testid="preset-enrollment-surge"]', state="visible", timeout=15000)

    rec.click('[data-testid="preset-enrollment-surge"]', duration=0.7, rx=0.5, ry=0.5)
    rec.hold(0.8)
    rec.move_to('[data-testid="growth-row"]', duration=0.6, rx=0.45, ry=0.5)
    rec.hold(0.9)

    _run_simulation_and_wait(
        rec,
        """() => {
            const btn = document.querySelector('[data-testid="run-scenario"]');
            const res = document.querySelector('[data-testid="whatif-result"]');
            return Boolean(res && btn && !btn.disabled);
        }""",
    )

    res_rect = rec._query_rect('[data-testid="whatif-result"]')
    if res_rect:
        cur_scroll = float(rec.page.evaluate("() => window.scrollY"))
        rec.scroll_to_y(cur_scroll + res_rect["top"] - 110.0, duration=0.7)

    rec.move_to('[data-testid="baseline-status"]', duration=0.55, auto_scroll=False)
    rec.hold(0.7)
    rec.move_to('[data-testid="scenario-status"]', duration=0.5, auto_scroll=False)
    rec.hold(0.8)
    tail_sel = '[data-testid="changed-courses"]' if rec._query_rect('[data-testid="changed-courses"]') else '[data-testid="metrics-table"]'
    rec.move_to(tail_sel, duration=0.65, rx=0.4, ry=0.5, auto_scroll=True)


def cue_12_whatif_preset2_buyout(rec: LiveRecorder) -> None:
    rec.scroll_to_y(0, duration=0.65)
    rec.click('[data-testid="preset-instructor-buyout"]', duration=0.75, rx=0.5, ry=0.5)
    rec.hold(0.7)
    rec.move_to('[data-testid="buyout-instructor"]', duration=0.6, rx=0.5, ry=0.5)
    rec.hold(0.8)
    rec.move_to('[data-testid="coverage-strategy"]', duration=0.55, rx=0.5, ry=0.5)
    rec.hold(0.8)

    _run_simulation_and_wait(
        rec,
        """() => {
            const btn = document.querySelector('[data-testid="run-scenario"]');
            const cov = document.querySelector('[data-testid="coverage-summary"]');
            return Boolean(cov && btn && !btn.disabled);
        }""",
    )

    cov_rect = rec._query_rect('[data-testid="coverage-summary"]')
    if cov_rect:
        cur_scroll = float(rec.page.evaluate("() => window.scrollY"))
        rec.scroll_to_y(cur_scroll + cov_rect["top"] - 220.0, duration=0.7)

    rec.move_to('[data-testid="coverage-summary"]', duration=0.65, rx=0.38, ry=0.5, auto_scroll=False)
    rec.hold(1.4)
    tail_sel = '[data-testid="changed-courses"]' if rec._query_rect('[data-testid="changed-courses"]') else '[data-testid="metrics-table"]'
    rec.move_to(tail_sel, duration=0.6, rx=0.4, ry=0.5, auto_scroll=False)


def cue_13_whatif_preset3_room(rec: LiveRecorder) -> None:
    rec.scroll_to_y(0, duration=0.65)
    rec.click('[data-testid="preset-room-reassigned"]', duration=0.75, rx=0.5, ry=0.5)
    rec.hold(0.7)
    rec.move_to('[data-testid="capacity-scale"]', duration=0.65, rx=0.45, ry=0.5)
    rec.hold(1.0)

    _run_simulation_and_wait(
        rec,
        """() => {
            const btn = document.querySelector('[data-testid="run-scenario"]');
            const cov = document.querySelector('[data-testid="coverage-summary"]');
            const res = document.querySelector('[data-testid="whatif-result"]');
            return Boolean(!cov && res && btn && !btn.disabled);
        }""",
    )

    res_rect = rec._query_rect('[data-testid="whatif-result"]')
    if res_rect:
        cur_scroll = float(rec.page.evaluate("() => window.scrollY"))
        rec.scroll_to_y(cur_scroll + res_rect["top"] - 95.0, duration=0.7)

    tail_sel = '[data-testid="changed-courses"]' if rec._query_rect('[data-testid="changed-courses"]') else '[data-testid="metrics-table"]'
    rec.move_to(tail_sel, duration=0.65, rx=0.42, ry=0.5, auto_scroll=True)
    rec.hold(1.8)
    rec.move_to('[data-testid="metrics-table"]', duration=0.65, rx=0.45, ry=0.45, auto_scroll=False)


def cue_14_commercialization_and_close(rec: LiveRecorder) -> None:
    rec.scroll_to_y(0, duration=0.6)
    rec.click('a[href="/commercialization"]', duration=0.75, rx=0.5, ry=0.5)
    rec.page.wait_for_selector('[data-testid="paste-input"]', state="visible", timeout=15000)
    rec.hold(0.5)

    rec.click('[data-testid="paste-input"]', duration=0.65, rx=0.35, ry=0.45)
    abstract_text = (
        "OptiSched: Uncertainty-Aware Academic Course Scheduling via Split-Conformal "
        "Prediction Intervals and Lexicographic CP-SAT Optimization\n"
        "Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro, Yugyung Lee, Sudipta Chattopadhyay\n"
        "Abstract: A central problem in university course scheduling is sizing classrooms "
        "months before registration opens when course demand is uncertain. We propose a novel "
        "predict-then-optimize framework combining pooled Ridge regression, split-conformal "
        "prediction intervals, and lexicographic CP-SAT constraint optimization. Compared with "
        "existing methods that copy prior-term enrollment or use uncalibrated point forecasts, "
        "our approach reduces unseated student seats by 61 percent across 40 held-out UIUC FOIA "
        "courses while maintaining zero hard conflicts.\n"
        "Keywords: conformal prediction, course timetabling, CP-SAT optimization, demand forecasting\n"
        "Acknowledgments: This work was supported by National Science Foundation (NSF) Award "
        "IIS-240192 at the University of Missouri-Kansas City."
    )
    rec.page.locator('[data-testid="paste-input"]').fill(abstract_text)
    rec.hold(1.0)

    rec.click('[data-testid="draft-button"]', duration=0.65, rx=0.5, ry=0.5)
    rec.page.wait_for_selector('[data-testid="draft-result"]', state="visible", timeout=15000)
    rec.hold(0.6)

    draft_rect = rec._query_rect('[data-testid="draft-result"]')
    if draft_rect:
        cur_scroll = float(rec.page.evaluate("() => window.scrollY"))
        rec.scroll_to_y(cur_scroll + draft_rect["top"] - 65.0, duration=0.75)

    rec.move_to('[data-testid="field-A1_title"]', duration=0.65, rx=0.45, ry=0.5, auto_scroll=False)
    rec.hold(2.0)
    rec.move_to('[data-testid="field-A1_novel"]', duration=0.65, rx=0.45, ry=0.5, auto_scroll=True)


BEAT_ACTIONS: dict[str, Callable[[LiveRecorder], None]] = {
    "intro_team": cue_01_intro_team,
    "problem_and_login": cue_02_problem_and_login,
    "foia_training_data": cue_03_foia_training_data,
    "ridge_and_conformal_chart": cue_04_ridge_and_conformal_chart,
    "live_course_switch": cue_05_live_course_switch,
    "benchmark_stage1": cue_06_benchmark_stage1,
    "benchmark_stage2": cue_07_benchmark_stage2,
    "unseated_comparison": cue_08_unseated_comparison,
    "data_evaluation_scope": cue_09_data_evaluation_scope,
    "master_schedule": cue_10_master_schedule,
    "whatif_preset1_surge": cue_11_whatif_preset1_surge,
    "whatif_preset2_buyout": cue_12_whatif_preset2_buyout,
    "whatif_preset3_room": cue_13_whatif_preset3_room,
    "commercialization_and_close": cue_14_commercialization_and_close,
}


def record_silent_video(ffmpeg_exe: str, durations: list[float], silent_mp4: Path) -> list[float]:
    if silent_mp4.exists():
        silent_mp4.unlink()

    ffmpeg_cmd = [
        ffmpeg_exe,
        "-y",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-framerate",
        str(FPS),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "fast",
        "-crf",
        "16",
        "-r",
        str(FPS),
        str(silent_mp4),
    ]
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    beat_start_times: list[float] = []
    cumulative_time = 0.0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        context.add_init_script(OVERLAY_INIT_JS)
        page = context.new_page()

        rec = LiveRecorder(page, ffmpeg_proc)
        for idx, (beat, dur) in enumerate(zip(BEATS, durations)):
            start_frame = round(cumulative_time * FPS)
            beat_start_times.append(cumulative_time)
            cumulative_time += dur
            target_total_frames = round(cumulative_time * FPS)
            rec.set_beat_caption(beat, start_frame, target_total_frames)
            BEAT_ACTIONS[beat.id](rec)
            actual_frames = rec.frames_emitted
            spillover = actual_frames - target_total_frames
            print(
                f"Cue {idx + 1:02d}/{len(BEATS)} ({beat.id}): actual_frames={actual_frames}, "
                f"target_total_frames={target_total_frames}, spillover={spillover} ({cumulative_time:.2f}s)"
            )
            if spillover > 0:
                raise RuntimeError(
                    f"Cue {idx + 1} ({beat.id}) spilled over by {spillover} frames "
                    f"(actual={actual_frames} > target={target_total_frames})"
                )
            rec.pad_until_frame(target_total_frames)

        context.close()
        browser.close()

    assert ffmpeg_proc.stdin is not None
    ffmpeg_proc.stdin.close()
    stderr_bytes = ffmpeg_proc.stderr.read() if ffmpeg_proc.stderr else b""
    ret = ffmpeg_proc.wait()
    if ret != 0:
        raise RuntimeError(f"ffmpeg video encode failed: {stderr_bytes.decode('utf-8', errors='replace')}")

    return beat_start_times


def _fmt_srt_time(seconds: float) -> str:
    ms_total = max(0, round(seconds * 1000))
    hrs, rem = divmod(ms_total, 3600000)
    mins, rem = divmod(rem, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def write_srt_subtitles(durations: list[float], srt_path: Path) -> None:
    import re

    entries: list[str] = []
    cue_idx = 1
    t_cursor = 0.0
    for beat, dur in zip(BEATS, durations):
        parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", beat.narration.strip()) if s.strip()]
        if len(parts) == 2 and len(parts[0]) <= 20:
            parts = [f"{parts[0]} {parts[1]}"]
        spoken_dur = max(0.5, dur - BEAT_PAD_SECONDS)
        total_chars = max(1, sum(len(s) for s in parts))
        sub_t = t_cursor
        for i, sent in enumerate(parts):
            seg_dur = (t_cursor + spoken_dur - sub_t) if i == len(parts) - 1 else spoken_dur * len(sent) / total_chars
            entries.append(f"{cue_idx}\n{_fmt_srt_time(sub_t)} --> {_fmt_srt_time(sub_t + seg_dur)}\n{sent}\n")
            cue_idx += 1
            sub_t += seg_dur
        t_cursor += dur
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("\n".join(entries), encoding="utf-8")


def mux_video_and_audio(ffmpeg_exe: str, silent_mp4: Path, master_wav: Path, final_mp4: Path, durations: list[float] | None = None) -> None:
    final_mp4.parent.mkdir(parents=True, exist_ok=True)
    srt_path = HACKATHON_DIR / "OptiSched_3Min_Demo.srt"
    if durations:
        write_srt_subtitles(durations, srt_path)
        shutil.copy2(srt_path, DOWNLOADS_DIR / "OptiSched_3Min_Demo.srt")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(silent_mp4),
        "-i",
        str(master_wav),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(final_mp4),
    ]
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def extract_verification_frames(
    ffmpeg_exe: str,
    final_mp4: Path,
    beat_starts: list[float],
    durations: list[float],
) -> None:
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    samples = [
        (0, 0.45, "verify_cue1_intro.png"),
        (2, 0.42, "verify_cue3_foia.png"),
        (3, 0.78, "verify_cue4_chart.png"),
        (5, 0.72, "verify_cue6_stage1.png"),
        (6, 0.72, "verify_cue7_stage2.png"),
        (7, 0.75, "verify_cue8_unseated.png"),
        (11, 0.85, "verify_cue12_whatif2.png"),
    ]
    for beat_idx, frac, filename in samples:
        ts = beat_starts[beat_idx] + durations[beat_idx] * frac
        out_png = SCRATCH_DIR / filename
        subprocess.run(
            [
                ffmpeg_exe,
                "-y",
                "-ss",
                f"{ts:.2f}",
                "-i",
                str(final_mp4),
                "-frames:v",
                "1",
                str(out_png),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Extracted verification frame {out_png} at {ts:.2f}s")


def main() -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print("Synthesizing neural voiceover across 14 cues...")
    master_wav, durations = generate_voiceover_and_durations(ffmpeg_exe)

    backend_proc: subprocess.Popen[bytes] | None = None
    frontend_proc: subprocess.Popen[bytes] | None = None

    try:
        if not http_ready(f"{BACKEND_URL}/api/v1/health"):
            print("Starting FastAPI backend on port 8000 (DATA_PROFILE=uiuc_foia)...")
            env = os.environ.copy()
            env["DATA_PROFILE"] = "uiuc_foia"
            env["SCENARIO_SOLVER_WORKERS"] = "8"
            backend_proc = subprocess.Popen(
                ["python3", "-m", "uvicorn", "app.main:app", "--port", "8000"],
                cwd=str(BACKEND_DIR),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_for_url(f"{BACKEND_URL}/api/v1/health", timeout_sec=45.0)

        if not http_ready(FRONTEND_URL):
            print("Starting Vite React frontend on port 5173...")
            frontend_proc = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "5173"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_for_url(FRONTEND_URL, timeout_sec=45.0)

        print("Warming up backend forecast, benchmark, and baseline CP-SAT solver...")
        warmup_backend()

        silent_out = DOWNLOADS_DIR / "OptiSched_3Min_Demo_NoVoice.mp4"
        silent_out.parent.mkdir(parents=True, exist_ok=True)
        print("Recording live 1920x1080 24fps Playwright browser session...")
        beat_starts = record_silent_video(ffmpeg_exe, durations, silent_out)

        primary_out = HACKATHON_DIR / "OptiSched_3Min_Demo.mp4"
        print("Muxing H.264 video stream with burned-in captions and neural voiceover audio...")
        mux_video_and_audio(ffmpeg_exe, silent_out, master_wav, primary_out, durations)

        for dest in (
            BRAIN_DIR / "OptiSched_3Min_Demo.mp4",
            DOWNLOADS_DIR / "OptiSched_3Min_Demo.mp4",
        ):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(primary_out, dest)
            print(f"Copied final video to {dest}")

        extract_verification_frames(ffmpeg_exe, primary_out, beat_starts, durations)
        print(f"Done! Primary video: {primary_out}")
    finally:
        if frontend_proc is not None:
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_proc.kill()
        if backend_proc is not None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_proc.kill()


if __name__ == "__main__":
    main()
