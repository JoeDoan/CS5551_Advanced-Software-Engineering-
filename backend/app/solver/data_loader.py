# -*- coding: utf-8 -*-
"""Data Loader and Repository for Course Scheduler Project.
Handles reading and writing the relational JSON database in backend/data/umkc/.
Validates relational integrity and foreign keys.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple

_SOLVER_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_SOLVER_DIR)
_BACKEND_DIR = os.path.dirname(_APP_DIR)
DATA_DIR = os.path.join(_BACKEND_DIR, "data", "umkc")


class DataLoader:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = DATA_DIR
        if not os.path.isabs(data_dir):
            candidate_backend = os.path.join(_BACKEND_DIR, data_dir)
            candidate_cwd = os.path.join(os.getcwd(), data_dir)
            if os.path.exists(candidate_backend):
                data_dir = candidate_backend
            elif os.path.exists(candidate_cwd):
                data_dir = candidate_cwd
            else:
                data_dir = os.path.abspath(data_dir)
        self.data_dir = data_dir
        self.campuses: List[Dict[str, Any]] = []
        self.buildings: List[Dict[str, Any]] = []
        self.rooms: List[Dict[str, Any]] = []
        self.users: List[Dict[str, Any]] = []
        self.courses: List[Dict[str, Any]] = []
        self.time_slots: List[Dict[str, Any]] = []
        self.semesters: List[Dict[str, Any]] = []
        self.instructor_preferences: List[Dict[str, Any]] = []
        self.schedules: List[Dict[str, Any]] = []
        self.edit_requests: List[Dict[str, Any]] = []
        self.load_all()

    def _load_json(self, filename: str) -> List[Dict[str, Any]]:
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, filename: str, data: Any):
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_all(self):
        """Loads all relational tables from JSON files."""
        self.campuses = self._load_json("campuses.json")
        self.buildings = self._load_json("buildings.json")
        self.rooms = self._load_json("rooms.json")
        self.users = self._load_json("users.json")
        self.courses = self._load_json("courses.json")
        self.time_slots = self._load_json("time_slots.json")
        self.semesters = self._load_json("semesters.json")
        self.instructor_preferences = self._load_json("instructor_preferences.json")
        self.schedules = self._load_json("schedules.json")
        self.edit_requests = self._load_json("edit_requests.json")

    def validate_integrity(self) -> Tuple[bool, List[str]]:
        """Validates primary key uniqueness and foreign key integrity."""
        errors = []

        campus_ids = {c["campus_id"] for c in self.campuses}
        building_ids = {b["building_id"] for b in self.buildings}
        room_ids = {r["room_id"] for r in self.rooms}
        user_ids = {u["user_id"] for u in self.users}
        course_ids = {c["course_id"] for c in self.courses}
        slot_ids = {s["slot_id"] for s in self.time_slots}
        semester_ids = {s["id"] for s in self.semesters}

        # Buildings -> Campus
        for b in self.buildings:
            if b.get("campus_id") not in campus_ids:
                errors.append(f"Building {b.get('building_id')} references non-existent campus_id {b.get('campus_id')}")

        # Rooms -> Building & Campus
        for r in self.rooms:
            if r.get("building_id") not in building_ids:
                errors.append(f"Room {r.get('room_id')} references non-existent building_id {r.get('building_id')}")
            if r.get("campus_id") and r.get("campus_id") not in campus_ids:
                errors.append(f"Room {r.get('room_id')} references non-existent campus_id {r.get('campus_id')}")

        # Preferences -> User, Course, Slot, Room, Semester
        for p in self.instructor_preferences:
            inst_id = p.get("instructor_id")
            if inst_id not in user_ids:
                errors.append(f"Preference {p.get('id')} references non-existent instructor_id {inst_id}")
            if p.get("course_id") is not None and p.get("course_id") not in course_ids:
                errors.append(f"Preference {p.get('id')} references non-existent course_id {p.get('course_id')}")
            if p.get("preferred_slot_id") is not None and p.get("preferred_slot_id") not in slot_ids:
                errors.append(f"Preference {p.get('id')} references non-existent preferred_slot_id {p.get('preferred_slot_id')}")
            if p.get("preferred_room_id") is not None and p.get("preferred_room_id") not in room_ids:
                errors.append(f"Preference {p.get('id')} references non-existent preferred_room_id {p.get('preferred_room_id')}")
            if p.get("semester_id") not in semester_ids:
                errors.append(f"Preference {p.get('id')} references non-existent semester_id {p.get('semester_id')}")

        return (len(errors) == 0, errors)

    # -------------------------------------------------------------
    # Helper Mappings & Lookups
    # -------------------------------------------------------------
    def get_instructors(self) -> List[Dict[str, Any]]:
        """Returns users who have role == 'instructor'."""
        return [u for u in self.users if u.get("role") == "instructor"]

    def get_instructor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for u in self.get_instructors():
            if u.get("name") == name:
                return u
        return None

    def get_instructor_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        for u in self.get_instructors():
            if u.get("user_id") == user_id:
                return u
        return None

    def get_room_by_number(self, room_number: str) -> Optional[Dict[str, Any]]:
        for r in self.rooms:
            if r.get("room_number") == room_number:
                return r
        return None

    def get_course_by_name(self, course_name: str) -> Optional[Dict[str, Any]]:
        for c in self.courses:
            if c.get("course_name") == course_name:
                return c
        return None

    def get_slots_dict(self) -> Dict[int, str]:
        """Returns {slot_id: '08:00 - 09:15', ...}."""
        return {
            s["slot_id"]: f"{s['start_time']} - {s['end_time']}"
            for s in sorted(self.time_slots, key=lambda x: x["slot_id"])
        }

    def get_semesters(self) -> List[Dict[str, Any]]:
        """Returns all semester records sorted by semester_id."""
        return sorted(self.semesters, key=lambda s: s.get("semester_id", s.get("id", 0)))

    def get_resolved_preference(self, instructor_id: int, course_id: Optional[int] = None,
                                semester_id: Optional[int] = None) -> Dict[str, Any]:
        """Resolves preferences for an instructor, checking per-course first, then global fallback.
        Filters by semester_id (defaults to 1 if None).
        """
        if semester_id is None:
            semester_id = 1

        course_pref = None
        global_pref = None

        for p in self.instructor_preferences:
            if p.get("semester_id") == semester_id and p.get("instructor_id") == instructor_id:
                if course_id is not None and p.get("course_id") == course_id:
                    course_pref = p
                    break
                elif p.get("course_id") is None:
                    global_pref = p

        chosen = course_pref if course_pref is not None else global_pref
        if not chosen:
            return {
                "days": set(),
                "slots": set(),
                "room_ids": set(),
                "room_numbers": set(),
                "layout": None,
                "has_preferences": False
            }

        # Normalize days
        days = set(chosen.get("preferred_days", []))

        # Normalize slots: support preferred_slots list or preferred_slot_id int
        slots = set()
        if "preferred_slots" in chosen and isinstance(chosen["preferred_slots"], list):
            slots.update(chosen["preferred_slots"])
        if chosen.get("preferred_slot_id") is not None:
            slots.add(chosen["preferred_slot_id"])

        # Normalize rooms: support preferred_room_id -> room_number
        room_ids = set()
        room_numbers = set()
        if chosen.get("preferred_room_id") is not None:
            r_id = chosen["preferred_room_id"]
            room_ids.add(r_id)
            for r in self.rooms:
                if r.get("room_id") == r_id:
                    room_numbers.add(r.get("room_number"))

        layout = chosen.get("preferred_layout")

        has_preferences = bool(days or slots or room_numbers or layout)

        return {
            "days": days,
            "slots": slots,
            "room_ids": room_ids,
            "room_numbers": room_numbers,
            "layout": layout,
            "has_preferences": has_preferences,
            "raw": chosen
        }

    def get_valid_ic_pairs(self) -> set:
        """Returns set of valid (instructor_name, course_name) pairs based on qualifications.
        If preferences explicitly specify course qualifications (course_id is not None),
        only those pairs are returned.
        If no preferences have course_id specified, returns all possible pairs.
        """
        inst_id_to_name = {u["user_id"]: u["name"] for u in self.get_instructors()}
        course_id_to_name = {c["course_id"]: c["course_name"] for c in self.courses}

        pairs = set()
        has_specific_course_qual = False
        for p in self.instructor_preferences:
            c_id = p.get("course_id")
            i_id = p.get("instructor_id")
            if c_id is not None and i_id in inst_id_to_name and c_id in course_id_to_name:
                has_specific_course_qual = True
                pairs.add((inst_id_to_name[i_id], course_id_to_name[c_id]))

        if not has_specific_course_qual:
            for u in self.get_instructors():
                for c in self.courses:
                    pairs.add((u["name"], c["course_name"]))

        return pairs

    def get_valid_rc_pairs(self) -> set:
        """Returns set of valid (room_number, course_name) pairs where room capacity >= course enrollment
        and course required_layout matches room layout_type."""
        pairs = set()
        for r in self.rooms:
            r_cap = r.get("capacity", 999)
            r_num = r.get("room_number")
            r_layout = r.get("layout_type")
            for c in self.courses:
                c_enroll = c.get("expected_enrollment", 0)
                c_name = c.get("course_name")
                c_req_layout = c.get("required_layout")
                if r_cap >= c_enroll:
                    if c_req_layout == "lab" and r_layout != "lab":
                        continue
                    pairs.add((r_num, c_name))
        return pairs

    def save_schedules(self, schedules_list: List[Dict[str, Any]]):
        """Saves generated schedule records to data/schedules.json."""
        self.schedules = schedules_list
        self._save_json("schedules.json", schedules_list)

    def save_users(self):
        """Persists updated user priority scores to data/users.json."""
        self._save_json("users.json", self.users)

    def reset_priorities(self):
        """Resets all users' priority_points to their base_priority."""
        for u in self.users:
            u["priority_points"] = u.get("base_priority", 100000)
        self.save_users()
