"""Save real OpenAlex and NIH RePORTER responses for a fixed list of broad topics.

Run from backend/:  python data/scripts/build_lookup_fixtures.py
Only these broad topic words are sent. Output: data/commercialization/fixtures/lookups.json
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.lookup_adapters import FIXTURE_PATH, fetch_awards, fetch_literature  # noqa: E402

TOPICS = [
    "bridge inspection", "structural health monitoring", "acoustic sensing", "machine learning",
    "cybersecurity", "medical device", "battery storage", "drug discovery", "crop monitoring",
    "photonics", "process control",
]


def main() -> None:
    topics = {}
    with httpx.Client(timeout=15, headers={"User-Agent": "OptiSched-hackathon (academic demo)"}) as c:
        for t in TOPICS:
            items = []
            for fetch in (fetch_literature, fetch_awards):
                try:
                    items += [i.model_dump() for i in fetch(t, c)]
                except httpx.HTTPError as e:
                    print(f"{t}: {fetch.__name__} failed: {e}")
                time.sleep(0.5)
            topics[t] = items
            print(t, len(items))
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(
        json.dumps({"retrieved": date.today().isoformat(), "topics": topics}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
