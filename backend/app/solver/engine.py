# -*- coding: utf-8 -*-
"""Adv Software - Scheduler Project
Course Timetabling using Google OR-Tools CP-SAT Solver
Features:
  - Relational JSON Data Layer (matching Campuses, Buildings, Rooms, Users, Courses, Time_slots, Preferences)
  - Room Capacity Hard Constraints (expected_enrollment <= room capacity)
  - Instructor Preferences (Days of week, Time slots, Specific Classrooms & Layout Types)
  - Per-course Preference Overrides with Global Fallback
  - Priority-based Optimization with Integer Weights (40% Day, 40% Slot, 20% Room/Layout)
  - Probabilistic Tie-Breaking for Equal-Priority Conflicts
  - Dynamic Priority Accumulation (Dissatisfaction Compensation & Gradual Decay)
  - Persistent Storage in data/users.json and Export to data/schedules.json
"""

import argparse
import datetime
import json
import os
import random
import sys
from typing import Optional, Dict, List, Any, Tuple
from ortools.sat.python import cp_model

try:
    from app.solver.data_loader import DataLoader
except ImportError:
    try:
        from .data_loader import DataLoader
    except ImportError:
        from data_loader import DataLoader

# =========================================================
# Configuration & Constants
# =========================================================
_SOLVER_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_SOLVER_DIR)
_BACKEND_DIR = os.path.dirname(_APP_DIR)
PROFILES_FILE = os.path.join(_BACKEND_DIR, "data", "scripts", "instructor_profiles.json")
BASE_PRIORITY = 100_000
DECAY_RATE = 10_000      # Gradual reduction toward base if 100% satisfied
COMPENSATION = 20_000    # Maximum bonus points if 0% satisfied

# Dimension integer weights (40% Day, 40% Slot, 20% Room/Layout)
# Per course: max 2 meeting days * 2 pts = 4 pts (40%)
#             max 1 slot * 4 pts = 4 pts (40%)
#             max 1 room * 2 pts = 2 pts (20%) (Layout match = 1 pt)
# Total max points per course = 10 pts
WEIGHT_DAY_PER_MEETING = 2
WEIGHT_SLOT = 4
WEIGHT_ROOM = 2

DATE = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


# =========================================================
# Profile Management & Data Mapping
# =========================================================
def load_profiles_from_data(loader: DataLoader = None, semester_id: Optional[int] = None) -> dict:
    """Builds the active profiles dictionary from data/umkc/users.json and data/umkc/instructor_preferences.json."""
    if loader is None:
        loader = DataLoader()

    profiles = {}
    for user in loader.get_instructors():
        name = user["name"]
        u_id = user["user_id"]
        base_p = user.get("base_priority", BASE_PRIORITY)
        curr_p = user.get("priority_points", base_p)

        # Global preference fallback (course_id is None)
        global_res = loader.get_resolved_preference(u_id, course_id=None, semester_id=semester_id)

        # Per-course preferences (if any specified for specific course_id)
        course_prefs = {}
        for c in loader.courses:
            c_res = loader.get_resolved_preference(u_id, course_id=c["course_id"], semester_id=semester_id)
            if c_res.get("raw") and c_res["raw"].get("course_id") == c["course_id"]:
                course_prefs[c["course_name"]] = {
                    "days": list(c_res["days"]),
                    "slots": list(c_res["slots"]),
                    "classrooms": list(c_res["room_numbers"]),
                    "layout": c_res["layout"]
                }

        profiles[name] = {
            "user_id": u_id,
            "base_priority": base_p,
            "current_priority": curr_p,
            "preferences": {
                "days": list(global_res["days"]),
                "slots": list(global_res["slots"]),
                "classrooms": list(global_res["room_numbers"]),
                "layout": global_res["layout"]
            },
            "course_preferences": course_prefs
        }
    return profiles


def get_metadata(loader: DataLoader = None):
    """Retrieves room capacities, course expected enrollments, and room layout types."""
    if loader is None:
        loader = DataLoader()
    room_caps = {r["room_number"]: r.get("capacity", 999) for r in loader.rooms}
    course_enrolls = {c["course_name"]: c.get("expected_enrollment", 0) for c in loader.courses}
    room_layouts = {r["room_number"]: r.get("layout_type") for r in loader.rooms}
    return room_caps, course_enrolls, room_layouts


def load_or_init_profiles(filepath=PROFILES_FILE, reset=False, loader: DataLoader = None, semester_id: Optional[int] = None):
    """Loads profiles from data layer, initializing defaults if needed."""
    if loader is None:
        loader = DataLoader()
    if reset:
        loader.reset_priorities()
    profiles = load_profiles_from_data(loader, semester_id=semester_id)
    save_profiles(profiles, filepath)
    return profiles


def save_profiles(profiles, filepath=PROFILES_FILE):
    """Saves updated instructor profiles to legacy JSON."""
    with open(filepath, "w") as f:
        json.dump(profiles, f, indent=2)


# =========================================================
# CP-SAT Model Formulation & Variable Management
# =========================================================
class PrunedVarDict(dict):
    """Dictionary that returns 0 for missing keys so solver.Value(...) returns 0 instead of KeyError."""
    def __missing__(self, key):
        return 0


def build_schedule_model(profiles, date, class_room, instructors, courses, slots,
                         seed=None, room_capacities=None, course_enrollments=None, room_layouts=None,
                         valid_ic_pairs=None, valid_rc_pairs=None,
                         min_courses_per_instructor=1, max_courses_per_instructor=2):
    """Builds CP-SAT model with hard constraints (including capacity) and preference optimization objective.
    Supports domain pruning via valid_ic_pairs (instructor-course qualifications) and valid_rc_pairs (room capacities).
    Enforces maximum teaching load (default 2 courses per instructor).
    """
    if seed is not None:
        random.seed(seed)

    model = cp_model.CpModel()

    # Domain qualification sets
    if valid_ic_pairs is None:
        valid_ic_pairs = {(i, c) for i in instructors for c in courses}
    if valid_rc_pairs is None:
        if room_capacities and course_enrollments:
            valid_rc_pairs = {
                (r, c) for r in class_room for c in courses
                if room_capacities.get(r, 999) >= course_enrollments.get(c, 0)
            }
        else:
            valid_rc_pairs = {(r, c) for r in class_room for c in courses}

    # 1. Decision Variables (Domain Pruned)
    # Z[i, c] = 1 if instructor is assigned to teach course (only for qualified pairs)
    Z = PrunedVarDict()
    for (i, c) in valid_ic_pairs:
        if i in instructors and c in courses:
            Z[i, c] = model.NewBoolVar(f'Z_{i}_{c}')

    # Y[r, s, i, c] = 1 if (room, slot) is chosen for (instructor, course) (only for valid room capacity pairs)
    Y = PrunedVarDict()
    for (i, c) in valid_ic_pairs:
        if i in instructors and c in courses:
            for r in class_room:
                if (r, c) in valid_rc_pairs:
                    for s in slots.keys():
                        Y[r, s, i, c] = model.NewBoolVar(f'Y_{r}_{s}_{i}_{c}')

    # X[d, r, s, i, c] = 1 if scheduled on day d, room r, slot s, instructor i, course c (only where Y exists)
    X = PrunedVarDict()
    for d in date:
        for (r, s, i, c) in list(Y.keys()):
            X[d, r, s, i, c] = model.NewBoolVar(f'X_{d}_{r}_{s}_{i}_{c}')

    # 2. Hard Constraints
    # Each course assigned to 1 to 2 instructors
    for c in courses:
        qualified_insts = [i for i in instructors if (i, c) in Z]
        if qualified_insts:
            model.Add(sum(Z[i, c] for i in qualified_insts) >= 1)
            model.Add(sum(Z[i, c] for i in qualified_insts) <= 2)

    # Each instructor assigned min_courses_per_instructor to max_courses_per_instructor courses (max 2)
    for i in instructors:
        qualified_courses = [c for c in courses if (i, c) in Z]
        if qualified_courses:
            model.Add(sum(Z[i, c] for c in qualified_courses) >= min_courses_per_instructor)
            model.Add(sum(Z[i, c] for c in qualified_courses) <= max_courses_per_instructor)

    # Link Z to Y: instructor gets exactly one (room, slot) per assigned course
    for (i, c) in list(Z.keys()):
        active_y = [Y[r, s, i, c] for r in class_room for s in slots.keys() if (r, s, i, c) in Y]
        model.Add(sum(active_y) == Z[i, c])

    # Link Y to X: exactly 2 meeting days per week for chosen combination
    for (r, s, i, c) in list(Y.keys()):
        active_x = [X[d, r, s, i, c] for d in date if (d, r, s, i, c) in X]
        model.Add(sum(active_x) == 2 * Y[r, s, i, c])

    # Instructor conflict: at most 1 class per instructor per time slot on any given day
    for d in date:
        for s in slots.keys():
            for i in instructors:
                active_x = [X[d, r, s, i, c] for r in class_room for c in courses if (d, r, s, i, c) in X]
                if active_x:
                    model.AddAtMostOne(active_x)

    # Classroom conflict: at most 1 class per room per time slot on any given day
    for d in date:
        for s in slots.keys():
            for r in class_room:
                active_x = [X[d, r, s, i, c] for i in instructors for c in courses if (d, r, s, i, c) in X]
                if active_x:
                    model.AddAtMostOne(active_x)

    # Hard Constraint: Room Capacity Check (safety check for unpruned models)
    if room_capacities and course_enrollments:
        for r in class_room:
            r_cap = room_capacities.get(r, 999)
            for c in courses:
                c_enroll = course_enrollments.get(c, 0)
                if r_cap < c_enroll:
                    for s in slots.keys():
                        for i in instructors:
                            if (r, s, i, c) in Y:
                                model.Add(Y[r, s, i, c] == 0)

    # 3. Soft Preference Objective with Integer Priority Weights & Probabilistic Tie-Breaking
    objective_terms = []
    effective_weights = {}

    for i in instructors:
        prof = profiles.get(i, {})
        base_p = prof.get("current_priority", BASE_PRIORITY)
        jitter = random.randint(1, 999)
        W_i = base_p + jitter
        effective_weights[i] = (base_p, jitter, W_i)

        default_prefs = prof.get("preferences", {})
        course_prefs = prof.get("course_preferences", {})

        for c in courses:
            if (i, c) not in Z:
                continue

            c_p = course_prefs.get(c, default_prefs)
            pref_days = set(c_p.get("days", []))
            pref_slots = set(c_p.get("slots", []))
            pref_rooms = set(c_p.get("classrooms", []))
            pref_layout = c_p.get("layout", None)

            # Day preference: 40% weight (2 pts per meeting day matched, max 2 days = 4 pts)
            if pref_days:
                for d in pref_days:
                    if d in date:
                        for r in class_room:
                            for s in slots.keys():
                                if (d, r, s, i, c) in X:
                                    objective_terms.append(W_i * WEIGHT_DAY_PER_MEETING * X[d, r, s, i, c])

            # Slot preference: 40% weight (4 pts per slot matched, max 1 slot = 4 pts)
            if pref_slots:
                for s in pref_slots:
                    if s in slots:
                        for r in class_room:
                            if (r, s, i, c) in Y:
                                objective_terms.append(W_i * WEIGHT_SLOT * Y[r, s, i, c])

            # Room preference: 20% weight
            if pref_rooms:
                for r in pref_rooms:
                    if r in class_room:
                        for s in slots.keys():
                            if (r, s, i, c) in Y:
                                objective_terms.append(W_i * WEIGHT_ROOM * Y[r, s, i, c])
            elif pref_layout and room_layouts:
                for r in class_room:
                    if room_layouts.get(r) == pref_layout:
                        for s in slots.keys():
                            if (r, s, i, c) in Y:
                                objective_terms.append(W_i * (WEIGHT_ROOM // 2) * Y[r, s, i, c])

    if objective_terms:
        model.Maximize(sum(objective_terms))

    return model, X, Y, Z, effective_weights


# =========================================================
# Post-Solve Evaluation & Priority Adjustment Engine
# =========================================================
def evaluate_satisfaction_and_update(solver, profiles, X, Y, Z, date, class_room, instructors, courses, slots,
                                     room_layouts=None, loader: DataLoader = None):
    """Evaluates satisfaction percentage for each instructor and computes updated priority scores."""
    satisfaction_report = {}

    for i in instructors:
        prof = profiles.get(i, {})
        default_prefs = prof.get("preferences", {})
        course_prefs = prof.get("course_preferences", {})

        assigned_courses = [c for c in courses if solver.Value(Z[i, c]) == 1]
        k_courses = len(assigned_courses)

        total_max_pts = 0
        total_achieved_pts = 0
        day_matches = 0
        slot_matches = 0
        room_matches = 0
        has_any_prefs = False
        any_days_specified = False
        any_slots_specified = False
        any_rooms_specified = False

        course_breakdown = []
        for c in assigned_courses:
            c_p = course_prefs.get(c, default_prefs)
            p_days = set(c_p.get("days", []))
            p_slots = set(c_p.get("slots", []))
            p_rooms = set(c_p.get("classrooms", []))
            p_layout = c_p.get("layout", None)

            if p_days:
                any_days_specified = True
            if p_slots:
                any_slots_specified = True
            if p_rooms or p_layout:
                any_rooms_specified = True

            if p_days or p_slots or p_rooms or p_layout:
                has_any_prefs = True

            c_max_day = (2 * WEIGHT_DAY_PER_MEETING) if p_days else 0
            c_max_slot = WEIGHT_SLOT if p_slots else 0
            c_max_room = WEIGHT_ROOM if p_rooms else ((WEIGHT_ROOM // 2) if (p_layout and room_layouts) else 0)
            c_total_max = c_max_day + c_max_slot + c_max_room
            total_max_pts += c_total_max

            # Check days assigned
            c_days = [d for d in date if any((d, r, s, i, c) in X and solver.Value(X[d, r, s, i, c]) == 1 for r in class_room for s in slots.keys())]
            matched_days = [d for d in c_days if d in p_days]
            if p_days:
                day_matches += len(matched_days)
                total_achieved_pts += len(matched_days) * WEIGHT_DAY_PER_MEETING

            # Check slot & room assigned
            c_slot = None
            c_room = None
            for s in slots.keys():
                for r in class_room:
                    if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1:
                        c_slot = s
                        c_room = r
                        break

            slot_matched = (c_slot in p_slots) if p_slots else None
            if slot_matched:
                slot_matches += 1
                total_achieved_pts += WEIGHT_SLOT

            room_matched = False
            if p_rooms:
                room_matched = (c_room in p_rooms)
                if room_matched:
                    room_matches += 1
                    total_achieved_pts += WEIGHT_ROOM
            elif p_layout and room_layouts:
                room_matched = (room_layouts.get(c_room) == p_layout)
                if room_matched:
                    room_matches += 1
                    total_achieved_pts += (WEIGHT_ROOM // 2)

            course_breakdown.append({
                "course": c,
                "days": c_days,
                "matched_days": matched_days,
                "slot": c_slot,
                "slot_matched": slot_matched,
                "room": c_room,
                "room_matched": room_matched,
            })

        if not has_any_prefs or total_max_pts == 0:
            satisfaction_report[i] = {
                "assigned_courses": assigned_courses,
                "has_preferences": False,
                "satisfaction_rate": None,
                "achieved_pts": 0,
                "max_pts": 0,
                "details": "No preferences specified",
                "old_priority": prof.get("current_priority", BASE_PRIORITY),
                "new_priority": prof.get("current_priority", BASE_PRIORITY),
                "delta": 0
            }
            continue

        satisfaction_rate = total_achieved_pts / total_max_pts
        old_p = prof.get("current_priority", BASE_PRIORITY)
        base_p = prof.get("base_priority", BASE_PRIORITY)

        # Priority Adjustment:
        # If 100% satisfied: gradual decay toward base
        # If < 100% satisfied: compensation proportional to unmet satisfaction
        if satisfaction_rate >= 0.999:
            new_p = max(base_p, old_p - DECAY_RATE)
            delta = new_p - old_p
        else:
            bonus = int(COMPENSATION * (1.0 - satisfaction_rate))
            new_p = old_p + bonus
            delta = bonus

        # Update profile and loader
        prof["current_priority"] = new_p
        if loader:
            u = loader.get_instructor_by_name(i)
            if u:
                u["priority_points"] = new_p

        satisfaction_report[i] = {
            "assigned_courses": assigned_courses,
            "has_preferences": True,
            "satisfaction_rate": satisfaction_rate,
            "achieved_pts": total_achieved_pts,
            "max_pts": total_max_pts,
            "day_matches": f"{day_matches}/{2 * k_courses}" if any_days_specified else "N/A",
            "slot_matches": f"{slot_matches}/{k_courses}" if any_slots_specified else "N/A",
            "room_matches": f"{room_matches}/{k_courses}" if any_rooms_specified else "N/A",
            "breakdown": course_breakdown,
            "old_priority": old_p,
            "new_priority": new_p,
            "delta": delta
        }

    return satisfaction_report


# =========================================================
# Schedule Export & Display
# =========================================================
def export_schedules(solver, X, Y, Z, loader: DataLoader, date, class_room, instructors, courses, slots, semester_id=1):
    """Exports solved schedule into data/schedules.json adhering to the Schedules table schema."""
    schedules_list = []
    schedule_id = 1

    inst_name_to_id = {u["name"]: u["user_id"] for u in loader.get_instructors()}
    course_name_to_id = {c["course_name"]: c["course_id"] for c in loader.courses}
    room_number_to_id = {r["room_number"]: r["room_id"] for r in loader.rooms}

    for c in courses:
        for i in instructors:
            if (i, c) in Z and solver.Value(Z[i, c]) == 1:
                assigned_room = None
                assigned_slot = None
                for r in class_room:
                    for s in slots.keys():
                        if (r, s, i, c) in Y and solver.Value(Y[r, s, i, c]) == 1:
                            assigned_room = r
                            assigned_slot = s
                            break
                    if assigned_room:
                        break

                assigned_days = [
                    d for d in date
                    if (d, assigned_room, assigned_slot, i, c) in X and solver.Value(X[d, assigned_room, assigned_slot, i, c]) == 1
                ]
                days_str = "/".join(assigned_days)

                schedules_list.append({
                    "schedule_id": schedule_id,
                    "course_id": course_name_to_id.get(c, 0),
                    "course_name": c,
                    "instructor_id": inst_name_to_id.get(i, 0),
                    "instructor_name": i,
                    "room_id": room_number_to_id.get(assigned_room, 0),
                    "room_number": assigned_room,
                    "slot_id": assigned_slot,
                    "days": days_str,
                    "semester_id": semester_id,
                    "status": "confirmed"
                })
                schedule_id += 1

    loader.save_schedules(schedules_list)
    return schedules_list


def print_schedule(solver, X, date, class_room, instructors, courses, slots):
    """Prints the weekly schedule in a clean format."""
    print("=" * 70)
    print("WEEKLY TIMETABLE")
    print("=" * 70)

    for d in date:
        print(f"\n--- {d.upper()} ---")
        day_classes = []
        for s_id in sorted(slots.keys()):
            for room in class_room:
                for inst in instructors:
                    for crs in courses:
                        if (d, room, s_id, inst, crs) in X and solver.Value(X[d, room, s_id, inst, crs]) == 1:
                            day_classes.append(
                                f"  Slot {s_id} ({slots[s_id]}) | Room {room:2} | {crs:<18} | Instructor: {inst}"
                            )
        if day_classes:
            print("\n".join(day_classes))
        else:
            print("  No classes scheduled.")


def print_satisfaction_and_priorities(satisfaction_report, effective_weights):
    """Prints a detailed satisfaction report and priority updates."""
    print("\n" + "=" * 70)
    print("INSTRUCTOR PREFERENCES & PRIORITY POINTS REPORT")
    print("=" * 70)
    header = f"{'Instructor':<24} | {'Priority (Old)':<14} | {'Jitter':<6} | {'Sat Rate':<8} | {'Days':<6} | {'Slot':<6} | {'Room':<6} | {'Priority (New)':<14}"
    print(header)
    print("-" * len(header))

    for inst, rep in satisfaction_report.items():
        old_p = f"{rep['old_priority']:,}"
        new_p = f"{rep['new_priority']:,}"
        if rep["delta"] > 0:
            new_p_str = f"{new_p} (+{rep['delta']:,})"
        elif rep["delta"] < 0:
            new_p_str = f"{new_p} ({rep['delta']:,})"
        else:
            new_p_str = f"{new_p} (no change)"

        if rep["has_preferences"]:
            jitter = effective_weights.get(inst, (0, 0, 0))[1]
            sat_str = f"{rep['satisfaction_rate'] * 100:>5.1f}%"
            day_str = rep["day_matches"]
            slot_str = rep["slot_matches"]
            room_str = rep["room_matches"]
        else:
            jitter = "-"
            sat_str = "N/A"
            day_str = "-"
            slot_str = "-"
            room_str = "-"

        print(f"{inst:<24} | {old_p:<14} | {str(jitter):<6} | {sat_str:<8} | {day_str:<6} | {slot_str:<6} | {room_str:<6} | {new_p_str:<14}")

    print("-" * len(header))
    print("Note: If preferences are not fully met, priority points increase for the next round.")
    print("      If preferences are 100% satisfied, priority points gradually decay toward 100,000.")


# =========================================================
# Main Execution & Simulation Engine
# =========================================================
def run_round(round_num=1, profiles=None, verbose=True, loader: DataLoader = None,
              max_courses_per_instructor=2, min_courses_per_instructor=1,
              semester_id=1, semester_name=None):
    """Executes a single scheduling round, updates profiles/users, exports schedule, and returns the report."""
    if loader is None:
        loader = DataLoader()

    if profiles is None:
        profiles = load_profiles_from_data(loader, semester_id=semester_id)

    slots = loader.get_slots_dict()
    date = DATE
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]

    room_caps, course_enrolls, room_layouts = get_metadata(loader)
    valid_ic = loader.get_valid_ic_pairs()
    valid_rc = loader.get_valid_rc_pairs()

    if verbose:
        print("\n" + "#" * 70)
        sem_str = f"{semester_name} (Semester {semester_id})" if semester_name else f"Semester {semester_id}"
        print(f"SCHEDULING ROUND {round_num}: {sem_str}")
        print("#" * 70)
        print(f"Total Classrooms:  {len(class_room)} ({', '.join(class_room[:6])}{'...' if len(class_room) > 6 else ''})")
        print(f"Total Instructors: {len(instructors)}")
        print(f"Total Courses:     {len(courses)}")
        print(f"Total Daily Slots: {len(slots)}")
        print(f"Max Teaching Load: {max_courses_per_instructor} courses / instructor")

    model, X, Y, Z, effective_weights = build_schedule_model(
        profiles, date, class_room, instructors, courses, slots,
        room_capacities=room_caps, course_enrollments=course_enrolls, room_layouts=room_layouts,
        valid_ic_pairs=valid_ic, valid_rc_pairs=valid_rc,
        min_courses_per_instructor=min_courses_per_instructor,
        max_courses_per_instructor=max_courses_per_instructor
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"[Error] No feasible schedule found for Round {round_num}.")
        return False, profiles

    status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
    if verbose:
        print(f"\nSchedule Found ({status_str}) in {solver.WallTime():.2f}s")
        print_schedule(solver, X, date, class_room, instructors, courses, slots)

    satisfaction_report = evaluate_satisfaction_and_update(
        solver, profiles, X, Y, Z, date, class_room, instructors, courses, slots,
        room_layouts=room_layouts, loader=loader
    )

    if verbose:
        print_satisfaction_and_priorities(satisfaction_report, effective_weights)

    # Persist updated priorities to users.json and instructor_profiles.json
    loader.save_users()
    save_profiles(profiles, PROFILES_FILE)

    # Export schedules to schedules.json and archive to schedules_sem{semester_id}.json
    export_schedules(solver, X, Y, Z, loader, date, class_room, instructors, courses, slots, semester_id=semester_id)
    archive_file = f"schedules_sem{semester_id}.json"
    loader._save_json(archive_file, loader.schedules)

    if verbose:
        print(f"\n[Saved] Updated instructor priorities saved to '{os.path.join(loader.data_dir, 'users.json')}' and '{PROFILES_FILE}'.")
        print(f"[Exported] Schedule timetable exported to '{os.path.join(loader.data_dir, 'schedules.json')}' and '{os.path.join(loader.data_dir, archive_file)}'.")

    return True, profiles


def main():
    parser = argparse.ArgumentParser(description="Course Scheduler with Relational JSON Database & Preferences.")
    parser.add_argument("--semesters", type=int, default=1, help="Number of consecutive semesters to simulate (1-6).")
    parser.add_argument("--simulate", type=int, default=1, help="Number of consecutive scheduling rounds per semester.")
    parser.add_argument("--reset", action="store_true", help="Reset instructor profiles and priorities to defaults.")
    args = parser.parse_args()

    loader = DataLoader()
    if args.reset:
        loader.reset_priorities()
        print(f"[Info] Instructor priorities in {os.path.join(loader.data_dir, 'users.json')} reset to defaults.")

    all_semesters = loader.get_semesters()
    num_semesters = max(1, min(args.semesters, len(all_semesters) if all_semesters else args.semesters))
    rounds_per_sem = max(1, args.simulate)

    overall_round = 1
    profiles = None

    for s_idx in range(num_semesters):
        sem = all_semesters[s_idx] if s_idx < len(all_semesters) else {"semester_id": s_idx + 1, "name": f"Semester {s_idx + 1}"}
        sem_id = sem.get("semester_id", sem.get("id", s_idx + 1))
        sem_name = sem.get("name", f"Semester {sem_id}")

        # Load profiles with this semester's preferences while preserving accumulated priorities
        profiles = load_profiles_from_data(loader, semester_id=sem_id)
        save_profiles(profiles, PROFILES_FILE)

        for r in range(1, rounds_per_sem + 1):
            success, profiles = run_round(
                round_num=overall_round, profiles=profiles, verbose=True, loader=loader,
                max_courses_per_instructor=2, min_courses_per_instructor=1,
                semester_id=sem_id, semester_name=sem_name
            )
            if not success:
                print(f"[Fatal] Scheduling failed at Semester {sem_id} ({sem_name}), Round {r}.")
                return
            overall_round += 1


if __name__ == "__main__":
    main()
