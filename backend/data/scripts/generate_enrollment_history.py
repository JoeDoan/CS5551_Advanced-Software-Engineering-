#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic enrollment history generator (seeded, reproducible).

The UMKC seed data holds a single `expected_enrollment` per course, so there is
no real history to learn from. This script builds a *clearly synthetic* history
for semesters 1-5 (Fall 2024 .. Fall 2026) so the forecasting pipeline can be
demonstrated and evaluated. Every row is tagged source="synthetic".

Generative process (latent level, then noise):
  level(c, t) = base(c) * (1 + g[dept]) ** (t - 5) * season(c, t) / season(c, 5)
  season(c, t) = 1 + a_c for Fall terms, 1 - a_c for Spring terms,
                 with a_c ~ U(0.04, 0.09) drawn once per course
  enrolled     = round(level * LogNormal(0, 0.04))
  shocks       = three course-semester pairs (terms 3-5) get +15% demand
  waitlist     = round(enrolled * (0.02 + 0.5 * max(g, 0)) * LogNormal(0, 0.3))
base(c) is courses.json expected_enrollment, so semester 5 is anchored to it.
Semester 6 (the forecast target) is intentionally NOT generated.

This only writes backend/data/umkc/enrollment_history.json and leaves every
other dataset file untouched. Run: python backend/data/scripts/generate_enrollment_history.py
"""

import json
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "umkc")
SEED = 5551
OBSERVED_SEMESTERS = (1, 2, 3, 4, 5)
FALL_SEMESTERS = {1, 3, 5}
# Per-semester demand growth by department (synthetic assumptions).
GROWTH = {
    "CS": 0.045,
    "ECE": 0.030,
    "STAT": 0.035,
    "BIOL": 0.020,
    "CHEM": 0.010,
    "MATH": 0.005,
    "PHYS": -0.010,
}
NOISE_SIGMA = 0.04
WAITLIST_SIGMA = 0.3
SHOCK_COUNT = 3
SHOCK_BOOST = 1.15


def generate(courses):
    rng = random.Random(SEED)
    amplitude = {c["course_id"]: rng.uniform(0.04, 0.09) for c in courses}
    shocks = set()
    while len(shocks) < SHOCK_COUNT:
        shocks.add((rng.choice(courses)["course_id"], rng.choice((3, 4, 5))))

    rows = []
    for c in courses:
        cid = c["course_id"]
        dept = c["course_name"].split()[0]
        g = GROWTH.get(dept, 0.0)
        a = amplitude[cid]

        def season(t, a=a):
            return 1 + a if t in FALL_SEMESTERS else 1 - a

        for t in OBSERVED_SEMESTERS:
            level = c["expected_enrollment"] * (1 + g) ** (t - 5) * season(t) / season(5)
            shocked = (cid, t) in shocks
            if shocked:
                level *= SHOCK_BOOST
            enrolled = max(1, round(level * rng.lognormvariate(0, NOISE_SIGMA)))
            waitlist_rate = 0.02 + 0.5 * max(g, 0.0) + (0.08 if shocked else 0.0)
            waitlist = max(0, round(enrolled * waitlist_rate * rng.lognormvariate(0, WAITLIST_SIGMA)))
            rows.append(
                {
                    "course_id": cid,
                    "semester_id": t,
                    "enrolled": enrolled,
                    "waitlist": waitlist,
                    "source": "synthetic",
                }
            )
    return rows


def main():
    with open(os.path.join(OUT_DIR, "courses.json"), "r", encoding="utf-8") as f:
        courses = json.load(f)
    rows = generate(courses)
    path = os.path.join(OUT_DIR, "enrollment_history.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"[Success] Wrote {len(rows)} synthetic observations to {path}")


if __name__ == "__main__":
    main()
