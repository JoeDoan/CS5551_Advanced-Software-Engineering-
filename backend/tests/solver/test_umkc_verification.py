#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UMKC Real-University Volume Dataset Verification Test Suite.
Tests the scheduler with the full UMKC School of Science & Engineering (SSE) dataset:
  - 20 faculty members
  - 40 courses
  - 12 classrooms
  - Maximum 2 classes per instructor per semester constraint
  - Course qualification purity via instructor_preferences.json
  - Room capacity hard constraints
  - Lab layout matching
  - Relational database export
  - Solver performance (< 10 seconds)
"""

import json
import os
import sys
import time
from ortools.sat.python import cp_model

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(os.path.dirname(_TEST_DIR))
_SOLVER_DIR = os.path.join(_BACKEND_DIR, "app", "solver")
_DATA_DIR = os.path.join(_BACKEND_DIR, "data", "umkc")
sys.path.insert(0, _SOLVER_DIR)

from data_loader import DataLoader
from engine import (
    build_schedule_model, evaluate_satisfaction_and_update,
    export_schedules, get_metadata, load_profiles_from_data,
    DATE
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
    print("UMKC REAL-UNIVERSITY VOLUME DATASET TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # TEST 1: Relational Integrity of UMKC Dataset
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 1: Relational Integrity of data/umkc/")
    print("=" * 70)
    loader = DataLoader(data_dir=_DATA_DIR)
    valid, errors = loader.validate_integrity()
    record("Foreign key integrity valid across all 10 UMKC JSON tables", valid,
           f"Errors: {errors}" if errors else "All foreign keys verified (Campuses, Buildings, Rooms, Users, Courses, Slots, Prefs)")

    record("Table sizes match UMKC specification",
           len(loader.users) == 20 and len(loader.courses) == 40 and len(loader.rooms) == 12 and len(loader.instructor_preferences) == 504 and len(loader.semesters) == 6,
           f"Users: {len(loader.users)} (exp 20), Courses: {len(loader.courses)} (exp 40), Rooms: {len(loader.rooms)} (exp 12), Prefs: {len(loader.instructor_preferences)} (exp 504), Semesters: {len(loader.semesters)} (exp 6)")

    # -------------------------------------------------------------
    # TEST 2: Solver Performance & Execution
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 2: Solver Performance (UMKC Scale: 20 Faculty, 40 Courses)")
    print("=" * 70)
    profiles = load_profiles_from_data(loader)
    slots = loader.get_slots_dict()
    date = DATE
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]
    room_caps, course_enrolls, room_layouts = get_metadata(loader)
    valid_ic = loader.get_valid_ic_pairs()
    valid_rc = loader.get_valid_rc_pairs()

    start_time = time.time()
    model, X, Y, Z, ew = build_schedule_model(
        profiles, date, class_room, instructors, courses, slots,
        room_capacities=room_caps, course_enrollments=course_enrolls, room_layouts=room_layouts,
        valid_ic_pairs=valid_ic, valid_rc_pairs=valid_rc,
        min_courses_per_instructor=1, max_courses_per_instructor=2,
        seed=42
    )
    build_time = time.time() - start_time

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solve_start = time.time()
    status = solver.Solve(model)
    solve_time = time.time() - solve_start
    total_time = build_time + solve_time

    is_solved = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
    record(f"UMKC model solved with {status_str} status", is_solved,
           f"Status: {status_str}, Variables build time: {build_time:.3f}s")
    record("Solve time under 10 seconds (Scalability Target)", solve_time <= 10.0,
           f"Wall solve time: {solve_time:.3f}s (Total: {total_time:.3f}s)")

    # -------------------------------------------------------------
    # TEST 3: Teaching Load Constraint (Max 2 classes per semester)
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 3: Maximum 2 Classes per Instructor Constraint")
    print("=" * 70)
    loads = {}
    exceeded_loads = []
    for i in instructors:
        assigned = [c for c in courses if solver.Value(Z[i, c]) == 1]
        loads[i] = len(assigned)
        if len(assigned) > 2:
            exceeded_loads.append((i, len(assigned)))

    all_under_or_equal_2 = len(exceeded_loads) == 0
    all_exactly_2 = all(loads[i] == 2 for i in instructors)
    record("No instructor teaches more than 2 classes in semester (Hard Constraint)",
           all_under_or_equal_2,
           f"Max load found: {max(loads.values())} courses" if not exceeded_loads else f"Exceeded: {exceeded_loads}")
    record("All 20 instructors assigned exactly 2 classes (40 courses / 20 faculty = 2.0)",
           all_exactly_2,
           f"Average load: {sum(loads.values()) / len(loads):.1f} courses/instructor")

    # -------------------------------------------------------------
    # TEST 4: Qualification Purity (Domain Filtering)
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 4: Qualification Purity (No Cross-Disciplinary Misassignment)")
    print("=" * 70)
    disqualified_assignments = []
    for i in instructors:
        for c in courses:
            if solver.Value(Z[i, c]) == 1:
                if (i, c) not in valid_ic:
                    disqualified_assignments.append((i, c))

    record("Zero unqualified course assignments (CS faculty teach CS, Math teach Math, etc.)",
           len(disqualified_assignments) == 0,
           f"Disqualified count: {len(disqualified_assignments)}" if disqualified_assignments else "All 40 assignments adhere strictly to instructor qualification records")

    # -------------------------------------------------------------
    # TEST 5: Room Capacity Hard Constraint
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 5: Room Capacity Hard Constraint Enforcement")
    print("=" * 70)
    capacity_violations = []
    course_assignments = {}
    for c in courses:
        for i in instructors:
            if solver.Value(Z[i, c]) == 1:
                for r in class_room:
                    for s in slots.keys():
                        if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1:
                            course_assignments[c] = (r, i, s)
                            cap = room_caps.get(r, 0)
                            enroll = course_enrolls.get(c, 0)
                            if cap < enroll:
                                capacity_violations.append((c, enroll, r, cap))

    record("No course placed in classroom smaller than expected enrollment",
           len(capacity_violations) == 0,
           f"Violations: {capacity_violations}" if capacity_violations else "All 40 courses satisfy capacity >= enrollment")

    # Specifically check large courses: BIOL 108 (140), MATH 110 (130), CS 101 (110), CHEM 211 (110)
    large_courses = ["BIOL 108 Intro Biology", "MATH 110 College Algebra", "CS 101 Intro to CS", "CHEM 211 Gen Chem I"]
    large_placed_correctly = True
    details = []
    for lc in large_courses:
        if lc in course_assignments:
            r, inst, s = course_assignments[lc]
            cap = room_caps.get(r, 0)
            enroll = course_enrolls.get(lc, 0)
            details.append(f"{lc} (enroll {enroll}) -> {r} (cap {cap})")
            if cap < enroll:
                large_placed_correctly = False
    record("Large enrollment courses (100+ students) correctly assigned to auditorium/large halls",
           large_placed_correctly, " | ".join(details))

    # -------------------------------------------------------------
    # TEST 6: Lab Layout Matching
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 6: Lab Layout Matching for Laboratory Courses")
    print("=" * 70)
    lab_courses = [c["course_name"] for c in loader.courses if c.get("required_layout") == "lab"]
    lab_assignments_correct = True
    lab_details = []
    for lc in lab_courses:
        if lc in course_assignments:
            r, inst, s = course_assignments[lc]
            layout = room_layouts.get(r)
            lab_details.append(f"{lc} in {r} ({layout})")
            if layout != "lab":
                lab_assignments_correct = False
    record("Lab courses (BIOL 109, ECE 380, ECE 448, CHEM 432) placed in dedicated lab rooms",
           lab_assignments_correct, " | ".join(lab_details))

    # -------------------------------------------------------------
    # TEST 7: No Double Booking (Instructors & Rooms)
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 7: Conflict-Free Scheduling (No Double Bookings)")
    print("=" * 70)
    inst_conflicts = 0
    room_conflicts = 0
    for d in date:
        for s in slots.keys():
            # Check instructor conflict
            for i in instructors:
                scheduled_count = sum(solver.Value(X[d, r, s, i, c]) for r in class_room for c in courses if (d, r, s, i, c) in X)
                if scheduled_count > 1:
                    inst_conflicts += 1
            # Check room conflict
            for r in class_room:
                scheduled_count = sum(solver.Value(X[d, r, s, i, c]) for i in instructors for c in courses if (d, r, s, i, c) in X)
                if scheduled_count > 1:
                    room_conflicts += 1

    record("Zero instructor time-slot conflicts across all days", inst_conflicts == 0,
           f"Conflicts: {inst_conflicts}")
    record("Zero classroom time-slot conflicts across all days", room_conflicts == 0,
           f"Conflicts: {room_conflicts}")

    # -------------------------------------------------------------
    # TEST 8: Schedule Export Verification
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 8: Schedule Export Verification to data/umkc/schedules.json")
    print("=" * 70)
    exported = export_schedules(solver, X, Y, Z, loader, date, class_room, instructors, courses, slots)
    record("Exported schedule contains exactly 40 course entries",
           len(exported) == 40,
           f"Count: {len(exported)} records exported")

    all_confirmed = all(rec.get("status") == "confirmed" for rec in exported)
    record("All exported records marked as 'confirmed'", all_confirmed)

    filepath = os.path.join(loader.data_dir, "schedules.json")
    record("data/umkc/schedules.json successfully written to disk",
           os.path.exists(filepath) and os.path.getsize(filepath) > 0,
           f"File path: {filepath} ({os.path.getsize(filepath)} bytes)")

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    passed_count = sum(1 for _, p in test_results if p)
    total_count = len(test_results)
    print(f"RESULTS: {passed_count}/{total_count} tests passed, {total_count - passed_count} failed")
    print("=" * 70)
    for name, p in test_results:
        print(f"  {PASS if p else FAIL} {name}")

    if passed_count == total_count:
        print(f"\nAll {total_count} UMKC tests PASSED successfully!")
        return 0
    else:
        print(f"\n{total_count - passed_count} tests FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
