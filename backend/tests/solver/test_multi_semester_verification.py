#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multi-Semester Verification Test Suite for UMKC Dataset.
Tests the scheduler across 6 distinct semesters with dynamic preference tables:
  1. Semester Table Integrity (6 semesters, valid dates, FK references)
  2. Preference Table Volume & Schema (504 entries, 84 per semester)
  3. Day Preference Rotation (>= 60% of faculty change preferred days)
  4. Time Slot Variation (Slots shift across semesters)
  5. Lab Room Constraint Purity (Lab courses only prefer lab rooms)
  6. Multi-Semester Simulation Execution (All 6 semesters solve successfully)
  7. Schedule Archive Creation (schedules_sem1.json through schedules_sem6.json)
  8. Constraint Compliance Across All Semesters (Capacity, max 2 courses, 0 double bookings)
  9. Priority Carryover Dynamics (Priorities carry over and evolve across terms)
  10. Inter-Semester Solution Diversity (Schedules differ across semesters)
"""

import json
import os
import sys
import time

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_TEST_DIR))
_SOLVER_DIR = os.path.join(_BACKEND_DIR, "app", "solver")
_DATA_DIR = os.path.join(_BACKEND_DIR, "data", "umkc")
sys.path.insert(0, _SOLVER_DIR)

from data_loader import DataLoader
from engine import (
    load_profiles_from_data, run_round, PROFILES_FILE, BASE_PRIORITY
)

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"

test_results = []


def record(name, passed, detail=""):
    status = PASS if passed else FAIL
    test_results.append((name, passed))
    print(f"  {status} {name}")
    if detail:
        print(f"         {detail}")


def main():
    print("=" * 70)
    print("MULTI-SEMESTER DYNAMIC PREFERENCE VERIFICATION TEST SUITE")
    print("=" * 70)

    loader = DataLoader(data_dir=_DATA_DIR)

    # -------------------------------------------------------------
    # TEST 1: Semester Table Integrity
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 1: Semester Table Integrity (6 Semesters)")
    print("=" * 70)
    semesters = loader.get_semesters()
    sem_count_ok = len(semesters) == 6
    sem_ids = [s.get("semester_id", s.get("id")) for s in semesters]
    sem_ids_ok = sem_ids == [1, 2, 3, 4, 5, 6]
    record("Exactly 6 semesters present (Fall 2024 - Spring 2027)", sem_count_ok and sem_ids_ok,
           f"Semesters found: {[s['name'] for s in semesters]}")

    # -------------------------------------------------------------
    # TEST 2: Preference Table Volume & Schema
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 2: Preference Table Volume & Schema (504 Entries)")
    print("=" * 70)
    total_prefs = len(loader.instructor_preferences)
    sem_counts = {}
    for p in loader.instructor_preferences:
        s_id = p.get("semester_id")
        sem_counts[s_id] = sem_counts.get(s_id, 0) + 1

    counts_ok = total_prefs == 504 and all(sem_counts.get(i) == 84 for i in range(1, 7))
    record("Total 504 preferences (84 per semester across 6 semesters)", counts_ok,
           f"Total: {total_prefs}, Counts per semester: {sem_counts}")

    # -------------------------------------------------------------
    # TEST 3: Day Preference Rotation (Statistical Check)
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 3: Day Preference Rotation Across Semesters")
    print("=" * 70)
    # Check what proportion of instructors change their preferred days across semesters
    instructors = loader.get_instructors()
    faculty_day_sets = {u["user_id"]: set() for u in instructors}

    for p in loader.instructor_preferences:
        u_id = p["instructor_id"]
        days_tuple = tuple(sorted(p.get("preferred_days", [])))
        if days_tuple:
            faculty_day_sets[u_id].add(days_tuple)

    rotated_faculty = [u_id for u_id, d_sets in faculty_day_sets.items() if len(d_sets) > 1]
    rotation_pct = (len(rotated_faculty) / len(instructors)) * 100
    record("At least 60% of faculty alternate preferred days across terms",
           rotation_pct >= 60.0,
           f"{len(rotated_faculty)} of {len(instructors)} faculty ({rotation_pct:.1f}%) rotate preferred days")

    # -------------------------------------------------------------
    # TEST 4: Time Slot Variation Across Semesters
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 4: Time Slot Variation Across Semesters")
    print("=" * 70)
    faculty_slot_sets = {u["user_id"]: set() for u in instructors}
    for p in loader.instructor_preferences:
        u_id = p["instructor_id"]
        slot_id = p.get("preferred_slot_id")
        if slot_id:
            faculty_slot_sets[u_id].add(slot_id)

    slot_varying_faculty = [u_id for u_id, s_sets in faculty_slot_sets.items() if len(s_sets) > 1]
    slot_var_pct = (len(slot_varying_faculty) / len(instructors)) * 100
    record("Faculty preferred slots shift across semesters",
           slot_var_pct >= 60.0,
           f"{len(slot_varying_faculty)} of {len(instructors)} faculty ({slot_var_pct:.1f}%) have varying preferred slots")

    # -------------------------------------------------------------
    # TEST 5: Lab Room Constraint Purity
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 5: Lab Room Preference Purity")
    print("=" * 70)
    lab_course_ids = {c["course_id"] for c in loader.courses if c.get("required_layout") == "lab"}
    lab_room_ids = {r["room_id"] for r in loader.rooms if r.get("layout_type") == "lab"}

    lab_pref_valid = True
    violating_prefs = []
    for p in loader.instructor_preferences:
        if p["course_id"] in lab_course_ids:
            if p.get("preferred_room_id") not in lab_room_ids:
                lab_pref_valid = False
                violating_prefs.append(p["id"])

    record("All lab course preferences exclusively request lab rooms (FH 464, FH 514, SCB 205)",
           lab_pref_valid,
           f"Violations: {len(violating_prefs)}")

    # -------------------------------------------------------------
    # TEST 6: Multi-Semester Simulation Execution
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 6: Multi-Semester Simulation Execution (6 Semesters)")
    print("=" * 70)
    loader.reset_priorities()

    semester_results = []
    overall_round = 1

    sim_start = time.time()
    for sem in semesters:
        sem_id = sem.get("semester_id", sem.get("id"))
        sem_name = sem.get("name")
        profiles = load_profiles_from_data(loader, semester_id=sem_id)

        success, profiles = run_round(
            round_num=overall_round, profiles=profiles, verbose=False, loader=loader,
            max_courses_per_instructor=2, min_courses_per_instructor=1,
            semester_id=sem_id, semester_name=sem_name
        )
        semester_results.append((sem_id, sem_name, success))
        overall_round += 1

    sim_duration = time.time() - sim_start
    all_solved = all(res[2] for res in semester_results)
    record("All 6 semesters successfully scheduled (100% solver success)", all_solved,
           f"Total wall time for 6 semesters: {sim_duration:.2f}s ({sim_duration / 6:.2f}s/sem)")

    # -------------------------------------------------------------
    # TEST 7: Schedule Archive Verification
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 7: Schedule Archive Verification (schedules_sem1..6.json)")
    print("=" * 70)
    archive_files_exist = True
    archive_counts = []
    for s_id in range(1, 7):
        fn = f"schedules_sem{s_id}.json"
        fp = os.path.join(loader.data_dir, fn)
        if not os.path.exists(fp):
            archive_files_exist = False
            break
        with open(fp, "r") as f:
            data = json.load(f)
            archive_counts.append(len(data))

    all_40 = archive_counts == [40] * 6
    record("Archived schedule files exist for all 6 semesters with 40 courses each",
           archive_files_exist and all_40,
           f"Archive files: schedules_sem1..6.json with counts {archive_counts}")

    # -------------------------------------------------------------
    # TEST 8: Constraint Compliance Across All 6 Semesters
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 8: Constraint Compliance Across All 6 Semesters")
    print("=" * 70)
    all_sem_compliant = True
    compliance_details = []

    room_caps = {r["room_number"]: r["capacity"] for r in loader.rooms}
    course_enrolls = {c["course_name"]: c["expected_enrollment"] for c in loader.courses}
    valid_ic = loader.get_valid_ic_pairs()

    for s_id in range(1, 7):
        fn = f"schedules_sem{s_id}.json"
        with open(os.path.join(loader.data_dir, fn), "r") as f:
            sched = json.load(f)

        # Check max 2 courses per instructor
        inst_counts = {}
        for entry in sched:
            inst = entry["instructor_name"]
            inst_counts[inst] = inst_counts.get(inst, 0) + 1
        if max(inst_counts.values()) > 2:
            all_sem_compliant = False
            compliance_details.append(f"Sem {s_id}: Max load {max(inst_counts.values())} > 2")

        # Check qualification purity
        for entry in sched:
            pair = (entry["instructor_name"], entry["course_name"])
            if pair not in valid_ic:
                all_sem_compliant = False
                compliance_details.append(f"Sem {s_id}: Unqualified {pair}")

        # Check room capacity
        for entry in sched:
            r_num = entry["room_number"]
            c_name = entry["course_name"]
            if room_caps.get(r_num, 0) < course_enrolls.get(c_name, 0):
                all_sem_compliant = False
                compliance_details.append(f"Sem {s_id}: Capacity overflow {c_name} in {r_num}")

        # Check zero double bookings
        room_slot_days = set()
        inst_slot_days = set()
        for entry in sched:
            slot = entry["slot_id"]
            room = entry["room_number"]
            inst = entry["instructor_name"]
            days = entry["days"].split("/")
            for d in days:
                if (room, slot, d) in room_slot_days:
                    all_sem_compliant = False
                    compliance_details.append(f"Sem {s_id}: Room conflict {room} at {slot} on {d}")
                room_slot_days.add((room, slot, d))

                if (inst, slot, d) in inst_slot_days:
                    all_sem_compliant = False
                    compliance_details.append(f"Sem {s_id}: Inst conflict {inst} at {slot} on {d}")
                inst_slot_days.add((inst, slot, d))

    record("Zero hard-constraint violations across all 6 semesters",
           all_sem_compliant,
           "Capacity, qualifications, max 2 classes, and zero double bookings confirmed across all 6 terms"
           if all_sem_compliant else f"Violations: {compliance_details[:3]}")

    # -------------------------------------------------------------
    # TEST 9: Priority Carryover Dynamics
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 9: Priority Carryover Dynamics After 6 Semesters")
    print("=" * 70)
    final_users = loader.users
    priorities = {u["name"]: u["priority_points"] for u in final_users}
    diff_from_base = {name: p - BASE_PRIORITY for name, p in priorities.items() if p != BASE_PRIORITY}

    record("Priority points dynamically evolved across 6 semesters",
           len(diff_from_base) > 0,
           f"{len(diff_from_base)} instructors have evolved priority scores (sample: {list(diff_from_base.items())[:4]})")

    # -------------------------------------------------------------
    # TEST 10: Inter-Semester Solution Diversity
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 10: Inter-Semester Solution Diversity")
    print("=" * 70)
    # Check that timetables across different semesters are not identical
    semester_fingerprints = []
    for s_id in range(1, 7):
        fn = f"schedules_sem{s_id}.json"
        with open(os.path.join(loader.data_dir, fn), "r") as f:
            sched = json.load(f)
        # Fingerprint: set of (course_name, instructor_name, room_number, slot_id, days)
        fp = frozenset((e["course_name"], e["instructor_name"], e["room_number"], e["slot_id"], e["days"]) for e in sched)
        semester_fingerprints.append(fp)

    unique_fps = len(set(semester_fingerprints))
    record("All 6 semesters produced distinct timetables",
           unique_fps == 6,
           f"{unique_fps} of 6 semesters have completely unique schedule assignments")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    passed_count = sum(1 for _, p in test_results if p)
    total_count = len(test_results)
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed_count}/{total_count} tests passed, {total_count - passed_count} failed")
    print("=" * 70)
    for name, p in test_results:
        status = PASS if p else FAIL
        print(f"  {status} {name}")

    if passed_count == total_count:
        print("\nAll Multi-Semester Verification tests PASSED successfully!")
        return 0
    else:
        print(f"\n[Warning] {total_count - passed_count} tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
