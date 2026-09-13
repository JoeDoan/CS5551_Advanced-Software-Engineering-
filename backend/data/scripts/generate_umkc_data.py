#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UMKC Real-University Volume Dataset Generator.
Generates a realistic 20-faculty, 40-course dataset modeled after
the UMKC School of Science & Engineering (SSE).
Outputs 10 relational JSON files into data/umkc/.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(BASE_DIR)  # backend/data/
OUT_DIR = os.path.join(DATA_DIR, "umkc")


def generate_umkc_dataset():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1. Campuses
    campuses = [
        {
            "campus_id": 1,
            "name": "Volker Campus",
            "address": "5100 Rockhill Rd, Kansas City, MO 64110"
        },
        {
            "campus_id": 2,
            "name": "Health Sciences Campus",
            "address": "2464 Charlotte St, Kansas City, MO 64108"
        }
    ]

    # 2. Buildings (Volker Campus)
    buildings = [
        {"building_id": 1, "campus_id": 1, "name": "Flarsheim Hall", "code": "FH"},
        {"building_id": 2, "campus_id": 1, "name": "Royall Hall", "code": "RH"},
        {"building_id": 3, "campus_id": 1, "name": "Haag Hall", "code": "HH"},
        {"building_id": 4, "campus_id": 1, "name": "Spencer Chemistry Building", "code": "SCB"},
        {"building_id": 5, "campus_id": 1, "name": "Bloch Heritage Hall", "code": "BHH"}
    ]

    # 3. Rooms (12 rooms, varied capacity & layout)
    rooms = [
        {"room_id": 1, "room_number": "SCB 101", "building_id": 4, "campus_id": 1, "capacity": 150, "layout_type": "auditorium"},
        {"room_id": 2, "room_number": "RH 204", "building_id": 2, "campus_id": 1, "capacity": 120, "layout_type": "lecture"},
        {"room_id": 3, "room_number": "FH 256", "building_id": 1, "campus_id": 1, "capacity": 80, "layout_type": "lecture"},
        {"room_id": 4, "room_number": "HH 301", "building_id": 3, "campus_id": 1, "capacity": 60, "layout_type": "lecture"},
        {"room_id": 5, "room_number": "RH 211", "building_id": 2, "campus_id": 1, "capacity": 50, "layout_type": "lecture"},
        {"room_id": 6, "room_number": "FH 310", "building_id": 1, "campus_id": 1, "capacity": 45, "layout_type": "lecture"},
        {"room_id": 7, "room_number": "HH 201", "building_id": 3, "campus_id": 1, "capacity": 45, "layout_type": "lecture"},
        {"room_id": 8, "room_number": "BHH 204", "building_id": 5, "campus_id": 1, "capacity": 40, "layout_type": "lecture"},
        {"room_id": 9, "room_number": "FH 464", "building_id": 1, "campus_id": 1, "capacity": 30, "layout_type": "lab"},
        {"room_id": 10, "room_number": "FH 514", "building_id": 1, "campus_id": 1, "capacity": 30, "layout_type": "lab"},
        {"room_id": 11, "room_number": "SCB 205", "building_id": 4, "campus_id": 1, "capacity": 28, "layout_type": "lab"},
        {"room_id": 12, "room_number": "FH 517", "building_id": 1, "campus_id": 1, "capacity": 25, "layout_type": "seminar"}
    ]

    # 4. Time Slots (6 standard 75-min slots)
    time_slots = [
        {"slot_id": 1, "start_time": "08:00", "end_time": "09:15"},
        {"slot_id": 2, "start_time": "09:30", "end_time": "10:45"},
        {"slot_id": 3, "start_time": "11:00", "end_time": "12:15"},
        {"slot_id": 4, "start_time": "12:30", "end_time": "13:45"},
        {"slot_id": 5, "start_time": "14:00", "end_time": "15:15"},
        {"slot_id": 6, "start_time": "15:30", "end_time": "16:45"}
    ]

    # 5. Semesters (6 semesters: Fall 2024 through Spring 2027)
    semesters = [
        {"semester_id": 1, "id": 1, "name": "Fall 2024", "start_date": "2024-08-26", "end_date": "2024-12-20", "is_active": False},
        {"semester_id": 2, "id": 2, "name": "Spring 2025", "start_date": "2025-01-21", "end_date": "2025-05-16", "is_active": False},
        {"semester_id": 3, "id": 3, "name": "Fall 2025", "start_date": "2025-08-25", "end_date": "2025-12-19", "is_active": False},
        {"semester_id": 4, "id": 4, "name": "Spring 2026", "start_date": "2026-01-20", "end_date": "2026-05-15", "is_active": False},
        {"semester_id": 5, "id": 5, "name": "Fall 2026", "start_date": "2026-08-24", "end_date": "2026-12-18", "is_active": True},
        {"semester_id": 6, "id": 6, "name": "Spring 2027", "start_date": "2027-01-19", "end_date": "2027-05-14", "is_active": False}
    ]

    # 6. Users (20 faculty members)
    # 6. Users (20 faculty members with realistic academic rank priorities)
    faculty_specs = [
        # CS / SE (8)
        (1, "Dr. Yugyung Lee", "leeyu@umkc.edu", 115000),         # Full Prof / CS Dept Chair
        (2, "Dr. Baek-Young Choi", "choiby@umkc.edu", 105000),     # Associate Prof
        (3, "Dr. Praveen Rao", "raopr@umkc.edu", 110000),          # Full Prof
        (4, "Dr. Reza Derakhshani", "derakhshanir@umkc.edu", 100000), # Associate Prof
        (5, "Dr. Sejun Song", "songse@umkc.edu", 105000),          # Associate Prof
        (6, "Dr. Zhu Li", "lizhu@umkc.edu", 100000),               # Associate Prof
        (7, "Dr. Cihan Tunc", "tuncc@umkc.edu", 100000),           # Assistant Prof
        (8, "Dr. Mohammad Kuhail", "kuhailm@umkc.edu", 100000),    # Assistant Teaching Prof
        # MATH / STAT (4)
        (9, "Dr. Majid Bani-Yaghoub", "baniyaghoubm@umkc.edu", 112000), # Full Prof / Math Dept Chair
        (10, "Dr. Noah Rhee", "rheen@umkc.edu", 100000),           # Full Prof
        (11, "Dr. Liana Sega", "segal@umkc.edu", 106000),          # Associate Prof
        (12, "Dr. Xianping Ge", "gex@umkc.edu", 100000),           # Assistant Prof
        # ECE / PHYS (4)
        (13, "Dr. Anthony Caruso", "carusoan@umkc.edu", 118000),   # Curators' Distinguished Prof / Vice Chancellor
        (14, "Dr. Deb Chatterjee", "chatterjeed@umkc.edu", 100000),# Associate Prof
        (15, "Dr. Ahmed Hassan", "hassana@umkc.edu", 105000),      # Associate Prof
        (16, "Dr. Masud Chowdhury", "chowdhurym@umkc.edu", 100000),# Full Prof
        # CHEM / BIOL (4)
        (17, "Dr. Kathleen Kilway", "kilwayk@umkc.edu", 120000),   # Curators' Distinguished Prof / Chem Chair
        (18, "Dr. Jeffrey Thomas", "thomasj@umkc.edu", 100000),    # Associate Prof
        (19, "Dr. Shin Moteki", "motekis@umkc.edu", 104000),       # Associate Prof
        (20, "Dr. Ryan Mohan", "mohanr@umkc.edu", 100000),         # Associate Prof
    ]

    users = []
    for u_id, name, email, priority in faculty_specs:
        users.append({
            "user_id": u_id,
            "name": name,
            "email": email,
            "role": "instructor",
            "campus_id": 1,
            "base_priority": priority,
            "priority_points": priority
        })

    # 7. Courses (40 total)
    course_specs = [
        # CS / SE (16)
        (1, "CS 101 Intro to CS", 110, "lecture"),
        (2, "CS 191 Discrete Structures", 75, "lecture"),
        (3, "CS 201R Prog II", 70, "lecture"),
        (4, "CS 281R Data Structures", 65, "lecture"),
        (5, "CS 303 Algorithms", 55, "lecture"),
        (6, "CS 394R Databases", 45, "lecture"),
        (7, "CS 404 Operating Systems", 40, "lecture"),
        (8, "CS 431 Software Eng", 45, "lecture"),
        (9, "CS 441 Programming Languages", 35, "lecture"),
        (10, "CS 451R Networks", 40, "lecture"),
        (11, "CS 456 Comp Arch", 35, "lecture"),
        (12, "CS 457 Info Security", 30, "lecture"),
        (13, "CS 461R AI", 50, "lecture"),
        (14, "CS 5551 Adv Software Eng", 35, "lecture"),
        (15, "CS 5553 Parallel Prog", 25, "lecture"),
        (16, "CS 5560 ML", 45, "lecture"),
        # MATH / STAT (8)
        (17, "MATH 110 College Algebra", 130, "lecture"),
        (18, "MATH 210 Calc I", 100, "lecture"),
        (19, "MATH 220 Calc II", 75, "lecture"),
        (20, "MATH 300 Linear Algebra", 50, "lecture"),
        (21, "MATH 345 Diff Eq", 40, "lecture"),
        (22, "MATH 410 Abstract Algebra", 25, "seminar"),
        (23, "STAT 235 Elem Stats", 60, "lecture"),
        (24, "STAT 436 Applied Stats", 35, "lecture"),
        # ECE / PHYS (8)
        (25, "ECE 216 Circuits I", 40, "lecture"),
        (26, "ECE 282 Digital Logic", 35, "lecture"),
        (27, "ECE 380 Microcontrollers", 28, "lab"),
        (28, "ECE 448 Embedded Systems", 25, "lab"),
        (29, "PHYS 210 Intro Mechanics", 90, "lecture"),
        (30, "PHYS 240 Physics I", 80, "lecture"),
        (31, "PHYS 250 Physics II", 60, "lecture"),
        (32, "PHYS 480 Quantum Mechanics", 20, "seminar"),
        # CHEM / BIOL (8)
        (33, "BIOL 108 Intro Biology", 140, "lecture"),
        (34, "BIOL 109 Biology Lab", 26, "lab"),
        (35, "BIOL 302 Genetics", 55, "lecture"),
        (36, "BIOL 410 Molecular Bio", 35, "lecture"),
        (37, "CHEM 211 Gen Chem I", 110, "lecture"),
        (38, "CHEM 212 Gen Chem II", 85, "lecture"),
        (39, "CHEM 330 Organic Chem", 50, "lecture"),
        (40, "CHEM 432 Biochemistry", 28, "lab"),
    ]

    courses = []
    for c_id, name, enroll, layout in course_specs:
        courses.append({
            "course_id": c_id,
            "course_name": name,
            "expected_enrollment": enroll,
            "required_layout": layout
        })

    # 8. Instructor Preferences & Qualifications
    # Mapping instructor_id -> list of qualified course_ids
    # Each instructor qualified for 4-5 courses in their field.
    # Each course has 2-3 qualified instructors.
    qualifications = {
        # CS Faculty (1-8)
        1: [1, 8, 13, 14, 16],        # CS 101, CS 431, CS 461R, CS 5551, CS 5560
        2: [2, 7, 9, 10, 15],         # CS 191, CS 404, CS 441, CS 451R, CS 5553
        3: [3, 4, 5, 6, 16],          # CS 201R, CS 281R, CS 303, CS 394R, CS 5560
        4: [1, 4, 12, 13],            # CS 101, CS 281R, CS 457, CS 461R
        5: [7, 10, 11, 15],           # CS 404, CS 451R, CS 456, CS 5553
        6: [3, 5, 11, 15],            # CS 201R, CS 303, CS 456, CS 5553
        7: [2, 4, 7, 12],             # CS 191, CS 281R, CS 404, CS 457
        8: [6, 8, 9, 14],             # CS 394R, CS 431, CS 441, CS 5551
        # Math Faculty (9-12)
        9: [17, 18, 21, 23],          # MATH 110, MATH 210, MATH 345, STAT 235
        10: [18, 19, 20, 22],         # MATH 210, MATH 220, MATH 300, MATH 410
        11: [19, 20, 22, 24],         # MATH 220, MATH 300, MATH 410, STAT 436
        12: [17, 21, 23, 24],         # MATH 110, MATH 345, STAT 235, STAT 436
        # ECE / Phys Faculty (13-16)
        13: [29, 30, 31, 32],         # PHYS 210, PHYS 240, PHYS 250, PHYS 480
        14: [25, 26, 29, 30, 31],     # ECE 216, ECE 282, PHYS 210, PHYS 240, PHYS 250
        15: [25, 26, 27, 28],         # ECE 216, ECE 282, ECE 380, ECE 448
        16: [25, 27, 28, 32],         # ECE 216, ECE 380, ECE 448, PHYS 480
        # Chem / Bio Faculty (17-20)
        17: [37, 38, 39, 40],         # CHEM 211, CHEM 212, CHEM 330, CHEM 432
        18: [33, 34, 35, 36],         # BIOL 108, BIOL 109, BIOL 302, BIOL 410
        19: [36, 37, 38, 39],         # BIOL 410, CHEM 211, CHEM 212, CHEM 330
        20: [33, 34, 35, 40],         # BIOL 108, BIOL 109, BIOL 302, CHEM 432
    }

    # Verify coverage: every course must have at least 2 qualified instructors
    course_to_instructors = {}
    for inst_id, c_list in qualifications.items():
        for c_id in c_list:
            course_to_instructors.setdefault(c_id, []).append(inst_id)

    missing = [c_id for c_id in range(1, 41) if len(course_to_instructors.get(c_id, [])) < 2]
    if missing:
        raise ValueError(f"Courses with < 2 qualified instructors: {missing}")

    def get_semester_conflicts(sem_id: int):
        """Returns semester-specific high-contention hotspot conflicts."""
        if sem_id == 1: # Fall 2024
            return {
                # CS Conflicts:
                (1, 13): (["Tuesday", "Thursday"], 2, 3), # Dr. Lee: CS 461R AI -> Slot 2, FH 256
                (4, 13): (["Tuesday", "Thursday"], 2, 3), # Dr. Derakhshani: CS 461R AI -> Slot 2, FH 256 [Direct Conflict]
                (3, 16): (["Tuesday", "Thursday"], 2, 3), # Dr. Rao: CS 5560 ML -> Slot 2, FH 256 [Direct Conflict]
                (1, 8):  (["Tuesday", "Thursday"], 3, 6), # Dr. Lee: CS 431 -> Slot 3, FH 310
                (8, 8):  (["Tuesday", "Thursday"], 3, 6), # Dr. Kuhail: CS 431 -> Slot 3, FH 310 [Direct Conflict]
                (3, 6):  (["Tuesday", "Thursday"], 3, 5), # Dr. Rao: CS 394R -> Slot 3, RH 211
                (8, 6):  (["Tuesday", "Thursday"], 3, 5), # Dr. Kuhail: CS 394R -> Slot 3, RH 211 [Direct Conflict]
                (1, 1):  (["Tuesday", "Thursday"], 2, 2), # Dr. Lee: CS 101 -> Slot 2, RH 204
                (4, 1):  (["Tuesday", "Thursday"], 2, 2), # Dr. Derakhshani: CS 101 -> Slot 2, RH 204 [Direct Conflict]
                (2, 10): (["Monday", "Wednesday"], 2, 3), # Dr. Choi: CS 451R -> Slot 2, FH 256
                (5, 10): (["Monday", "Wednesday"], 2, 3), # Dr. Song: CS 451R -> Slot 2, FH 256 [Direct Conflict]
                # Math Conflicts:
                (9, 18):  (["Tuesday", "Thursday"], 2, 2), # Dr. Bani-Yaghoub: MATH 210 -> Slot 2, RH 204
                (10, 18): (["Tuesday", "Thursday"], 2, 2), # Dr. Rhee: MATH 210 -> Slot 2, RH 204 [Direct Conflict]
                (11, 24): (["Monday", "Wednesday"], 3, 4), # Dr. Sega: STAT 436 -> Slot 3, HH 301
                (12, 24): (["Monday", "Wednesday"], 3, 4), # Dr. Ge: STAT 436 -> Slot 3, HH 301 [Direct Conflict]
                # ECE / Phys Conflicts:
                (15, 27): (["Tuesday", "Thursday"], 4, 10), # Dr. Hassan: ECE 380 -> Slot 4, FH 514 (lab)
                (16, 27): (["Tuesday", "Thursday"], 4, 10), # Dr. Chowdhury: ECE 380 -> Slot 4, FH 514 (lab) [Direct Conflict]
                (13, 30): (["Monday", "Wednesday"], 2, 2),  # Dr. Caruso: PHYS 240 -> Slot 2, RH 204
                (14, 30): (["Monday", "Wednesday"], 2, 2),  # Dr. Chatterjee: PHYS 240 -> Slot 2, RH 204 [Direct Conflict]
                # Chem / Bio Conflicts:
                (17, 37): (["Tuesday", "Thursday"], 2, 1), # Dr. Kilway: CHEM 211 -> Slot 2, SCB 101
                (19, 37): (["Tuesday", "Thursday"], 2, 1), # Dr. Moteki: CHEM 211 -> Slot 2, SCB 101 [Direct Conflict]
                (18, 34): (["Monday", "Wednesday"], 4, 11), # Dr. Thomas: BIOL 109 -> Slot 4, SCB 205 (lab)
                (20, 34): (["Monday", "Wednesday"], 4, 11), # Dr. Mohan: BIOL 109 -> Slot 4, SCB 205 (lab) [Direct Conflict]
                (17, 40): (["Tuesday", "Thursday"], 4, 11), # Dr. Kilway: CHEM 432 -> Slot 4, SCB 205 (lab)
                (20, 40): (["Tuesday", "Thursday"], 4, 9),  # Dr. Mohan: CHEM 432 -> Slot 4, FH 464 (lab)
            }
        elif sem_id == 2: # Spring 2025
            return {
                # CS Conflicts:
                (1, 13): (["Monday", "Wednesday"], 2, 3), # Dr. Lee: CS 461R -> Mon/Wed Slot 2, FH 256
                (2, 7):  (["Monday", "Wednesday"], 2, 3), # Dr. Choi: CS 404 -> Mon/Wed Slot 2, FH 256 [Direct Conflict]
                (5, 7):  (["Monday", "Wednesday"], 2, 3), # Dr. Song: CS 404 -> Mon/Wed Slot 2, FH 256 [Direct Conflict]
                (1, 14): (["Monday", "Wednesday"], 3, 6), # Dr. Lee: CS 5551 -> Mon/Wed Slot 3, FH 310
                (8, 14): (["Monday", "Wednesday"], 3, 6), # Dr. Kuhail: CS 5551 -> Mon/Wed Slot 3, FH 310 [Direct Conflict]
                (3, 4):  (["Tuesday", "Thursday"], 2, 3),  # Dr. Rao: CS 281R -> Tue/Thu Slot 2, FH 256
                (4, 4):  (["Tuesday", "Thursday"], 2, 3),  # Dr. Derakhshani: CS 281R -> Tue/Thu Slot 2, FH 256 [Direct Conflict]
                (7, 4):  (["Tuesday", "Thursday"], 2, 3),  # Dr. Tunc: CS 281R -> Tue/Thu Slot 2, FH 256 [Direct Conflict]
                # Math Conflicts:
                (9, 17):  (["Monday", "Wednesday"], 2, 2),  # Dr. Bani-Yaghoub: MATH 110 -> Mon/Wed Slot 2, RH 204
                (12, 17): (["Monday", "Wednesday"], 2, 2), # Dr. Ge: MATH 110 -> Mon/Wed Slot 2, RH 204 [Direct Conflict]
                (10, 20): (["Tuesday", "Thursday"], 3, 4), # Dr. Rhee: MATH 300 -> Tue/Thu Slot 3, HH 301
                (11, 20): (["Tuesday", "Thursday"], 3, 4), # Dr. Sega: MATH 300 -> Tue/Thu Slot 3, HH 301 [Direct Conflict]
                # ECE / Phys Conflicts:
                (13, 31): (["Monday", "Wednesday"], 3, 2),  # Dr. Caruso: PHYS 250 -> Mon/Wed Slot 3, RH 204
                (14, 31): (["Monday", "Wednesday"], 3, 2),  # Dr. Chatterjee: PHYS 250 -> Mon/Wed Slot 3, RH 204 [Direct Conflict]
                (15, 28): (["Tuesday", "Thursday"], 4, 10), # Dr. Hassan: ECE 448 -> Tue/Thu Slot 4, FH 514 (lab)
                (16, 28): (["Tuesday", "Thursday"], 4, 10), # Dr. Chowdhury: ECE 448 -> Tue/Thu Slot 4, FH 514 (lab) [Direct Conflict]
                # Chem / Bio Conflicts:
                (17, 39): (["Monday", "Wednesday"], 2, 1), # Dr. Kilway: CHEM 330 -> Mon/Wed Slot 2, SCB 101
                (19, 39): (["Monday", "Wednesday"], 2, 1), # Dr. Moteki: CHEM 330 -> Mon/Wed Slot 2, SCB 101 [Direct Conflict]
                (18, 35): (["Tuesday", "Thursday"], 3, 5), # Dr. Thomas: BIOL 302 -> Tue/Thu Slot 3, RH 211
                (20, 35): (["Tuesday", "Thursday"], 3, 5), # Dr. Mohan: BIOL 302 -> Tue/Thu Slot 3, RH 211 [Direct Conflict]
                (18, 34): (["Tuesday", "Thursday"], 4, 11),# BIOL 109 -> Tue/Thu Slot 4, SCB 205 (lab)
                (20, 34): (["Tuesday", "Thursday"], 4, 11),
            }
        elif sem_id == 3: # Fall 2025
            return {
                # CS Conflicts:
                (1, 16): (["Tuesday", "Thursday"], 3, 3), # Dr. Lee: CS 5560 -> Tue/Thu Slot 3, FH 256
                (3, 16): (["Tuesday", "Thursday"], 3, 3), # Dr. Rao: CS 5560 -> Tue/Thu Slot 3, FH 256 [Direct Conflict]
                (4, 13): (["Tuesday", "Thursday"], 3, 3), # Dr. Derakhshani: CS 461R -> Tue/Thu Slot 3, FH 256 [Direct Conflict]
                (1, 8):  (["Tuesday", "Thursday"], 2, 6), # Dr. Lee: CS 431 -> Tue/Thu Slot 2, FH 310
                (8, 8):  (["Tuesday", "Thursday"], 2, 6), # Dr. Kuhail: CS 431 -> Tue/Thu Slot 2, FH 310 [Direct Conflict]
                (2, 9):  (["Monday", "Wednesday"], 3, 5), # Dr. Choi: CS 441 -> Mon/Wed Slot 3, RH 211
                (8, 9):  (["Monday", "Wednesday"], 3, 5), # Dr. Kuhail: CS 441 -> Mon/Wed Slot 3, RH 211 [Direct Conflict]
                (5, 11): (["Monday", "Wednesday"], 4, 6), # Dr. Song: CS 456 -> Mon/Wed Slot 4, FH 310
                (6, 11): (["Monday", "Wednesday"], 4, 6), # Dr. Li: CS 456 -> Mon/Wed Slot 4, FH 310 [Direct Conflict]
                # Math Conflicts:
                (9, 21):  (["Tuesday", "Thursday"], 3, 4),  # Dr. Bani-Yaghoub: MATH 345 -> Tue/Thu Slot 3, HH 301
                (12, 21): (["Tuesday", "Thursday"], 3, 4), # Dr. Ge: MATH 345 -> Tue/Thu Slot 3, HH 301 [Direct Conflict]
                (10, 19): (["Tuesday", "Thursday"], 2, 2), # Dr. Rhee: MATH 220 -> Tue/Thu Slot 2, RH 204
                (11, 19): (["Tuesday", "Thursday"], 2, 2), # Dr. Sega: MATH 220 -> Tue/Thu Slot 2, RH 204 [Direct Conflict]
                # ECE / Phys Conflicts:
                (13, 29): (["Monday", "Wednesday"], 2, 2), # Dr. Caruso: PHYS 210 -> Mon/Wed Slot 2, RH 204
                (14, 29): (["Monday", "Wednesday"], 2, 2), # Dr. Chatterjee: PHYS 210 -> Mon/Wed Slot 2, RH 204 [Direct Conflict]
                (15, 27): (["Tuesday", "Thursday"], 5, 10),# Dr. Hassan: ECE 380 -> Tue/Thu Slot 5, FH 514 (lab)
                (16, 27): (["Tuesday", "Thursday"], 5, 10),# Dr. Chowdhury: ECE 380 -> Tue/Thu Slot 5, FH 514 (lab) [Direct Conflict]
                # Chem / Bio Conflicts:
                (17, 38): (["Tuesday", "Thursday"], 3, 1), # Dr. Kilway: CHEM 212 -> Tue/Thu Slot 3, SCB 101
                (19, 38): (["Tuesday", "Thursday"], 3, 1), # Dr. Moteki: CHEM 212 -> Tue/Thu Slot 3, SCB 101 [Direct Conflict]
                (18, 33): (["Monday", "Wednesday"], 2, 1), # Dr. Thomas: BIOL 108 -> Mon/Wed Slot 2, SCB 101
                (20, 33): (["Monday", "Wednesday"], 2, 1), # Dr. Mohan: BIOL 108 -> Mon/Wed Slot 2, SCB 101 [Direct Conflict]
                (17, 40): (["Tuesday", "Thursday"], 4, 9), # CHEM 432 -> FH 464 (lab)
                (20, 40): (["Tuesday", "Thursday"], 4, 9),
            }
        elif sem_id == 4: # Spring 2026
            return {
                # CS Conflicts:
                (1, 1):  (["Monday", "Wednesday"], 2, 2),  # Dr. Lee: CS 101 -> Mon/Wed Slot 2, RH 204
                (4, 1):  (["Monday", "Wednesday"], 2, 2),  # Dr. Derakhshani: CS 101 -> Mon/Wed Slot 2, RH 204 [Direct Conflict]
                (2, 2):  (["Monday", "Wednesday"], 2, 2),  # Dr. Choi: CS 191 -> Mon/Wed Slot 2, RH 204 [Direct Conflict]
                (7, 2):  (["Monday", "Wednesday"], 2, 2),  # Dr. Tunc: CS 191 -> Mon/Wed Slot 2, RH 204 [Direct Conflict]
                (3, 5):  (["Tuesday", "Thursday"], 2, 3),  # Dr. Rao: CS 303 -> Tue/Thu Slot 2, FH 256
                (6, 5):  (["Tuesday", "Thursday"], 2, 3),  # Dr. Li: CS 303 -> Tue/Thu Slot 2, FH 256 [Direct Conflict]
                (1, 13): (["Monday", "Wednesday"], 3, 3), # Dr. Lee: CS 461R -> Mon/Wed Slot 3, FH 256
                (5, 10): (["Monday", "Wednesday"], 3, 3), # Dr. Song: CS 451R -> Mon/Wed Slot 3, FH 256 [Direct Conflict]
                # Math Conflicts:
                (9, 23):  (["Monday", "Wednesday"], 3, 4),  # Dr. Bani-Yaghoub: STAT 235 -> Mon/Wed Slot 3, HH 301
                (12, 23): (["Monday", "Wednesday"], 3, 4), # Dr. Ge: STAT 235 -> Mon/Wed Slot 3, HH 301 [Direct Conflict]
                (10, 22): (["Tuesday", "Thursday"], 4, 12),# Dr. Rhee: MATH 410 -> Tue/Thu Slot 4, FH 517 (seminar)
                (11, 22): (["Tuesday", "Thursday"], 4, 12),# Dr. Sega: MATH 410 -> Tue/Thu Slot 4, FH 517 (seminar) [Direct Conflict]
                # ECE / Phys Conflicts:
                (13, 32): (["Monday", "Wednesday"], 4, 12),# Dr. Caruso: PHYS 480 -> Mon/Wed Slot 4, FH 517 (seminar)
                (16, 32): (["Monday", "Wednesday"], 4, 12),# Dr. Chowdhury: PHYS 480 -> Mon/Wed Slot 4, FH 517 (seminar) [Direct Conflict]
                (14, 26): (["Tuesday", "Thursday"], 3, 5), # Dr. Chatterjee: ECE 282 -> Tue/Thu Slot 3, RH 211
                (15, 26): (["Tuesday", "Thursday"], 3, 5), # Dr. Hassan: ECE 282 -> Tue/Thu Slot 3, RH 211 [Direct Conflict]
                # Chem / Bio Conflicts:
                (17, 37): (["Monday", "Wednesday"], 2, 1), # Dr. Kilway: CHEM 211 -> Mon/Wed Slot 2, SCB 101
                (19, 37): (["Monday", "Wednesday"], 2, 1), # Dr. Moteki: CHEM 211 -> Mon/Wed Slot 2, SCB 101 [Direct Conflict]
                (18, 36): (["Tuesday", "Thursday"], 3, 5), # Dr. Thomas: BIOL 410 -> Tue/Thu Slot 3, RH 211
                (19, 36): (["Tuesday", "Thursday"], 3, 5), # Dr. Moteki: BIOL 410 -> Tue/Thu Slot 3, RH 211 [Direct Conflict]
                (18, 34): (["Tuesday", "Thursday"], 4, 11),# BIOL 109 -> Tue/Thu Slot 4, SCB 205 (lab)
                (20, 34): (["Tuesday", "Thursday"], 4, 11),
            }
        elif sem_id == 5: # Fall 2026
            return {
                # CS Conflicts:
                (1, 14): (["Tuesday", "Thursday"], 2, 6), # Dr. Lee: CS 5551 -> Tue/Thu Slot 2, FH 310
                (8, 14): (["Tuesday", "Thursday"], 2, 6), # Dr. Kuhail: CS 5551 -> Tue/Thu Slot 2, FH 310 [Direct Conflict]
                (3, 3):  (["Tuesday", "Thursday"], 3, 3),  # Dr. Rao: CS 201R -> Tue/Thu Slot 3, FH 256
                (6, 3):  (["Tuesday", "Thursday"], 3, 3),  # Dr. Li: CS 201R -> Tue/Thu Slot 3, FH 256 [Direct Conflict]
                (4, 1):  (["Tuesday", "Thursday"], 2, 2),  # Dr. Derakhshani: CS 101 -> Tue/Thu Slot 2, RH 204
                (1, 1):  (["Tuesday", "Thursday"], 2, 2),  # Dr. Lee: CS 101 -> Tue/Thu Slot 2, RH 204 [Direct Conflict]
                (2, 15): (["Monday", "Wednesday"], 4, 12),# Dr. Choi: CS 5553 -> Mon/Wed Slot 4, FH 517
                (5, 15): (["Monday", "Wednesday"], 4, 12),# Dr. Song: CS 5553 -> Mon/Wed Slot 4, FH 517 [Direct Conflict]
                (6, 15): (["Monday", "Wednesday"], 4, 12),# Dr. Li: CS 5553 -> Mon/Wed Slot 4, FH 517 [Direct Conflict]
                # Math Conflicts:
                (9, 18):  (["Tuesday", "Thursday"], 3, 2),  # Dr. Bani-Yaghoub: MATH 210 -> Tue/Thu Slot 3, RH 204
                (10, 18): (["Tuesday", "Thursday"], 3, 2), # Dr. Rhee: MATH 210 -> Tue/Thu Slot 3, RH 204 [Direct Conflict]
                (11, 24): (["Monday", "Wednesday"], 2, 4), # Dr. Sega: STAT 436 -> Mon/Wed Slot 2, HH 301
                (12, 24): (["Monday", "Wednesday"], 2, 4), # Dr. Ge: STAT 436 -> Mon/Wed Slot 2, HH 301 [Direct Conflict]
                # ECE / Phys Conflicts:
                (13, 30): (["Monday", "Wednesday"], 3, 2), # Dr. Caruso: PHYS 240 -> Mon/Wed Slot 3, RH 204
                (14, 30): (["Monday", "Wednesday"], 3, 2), # Dr. Chatterjee: PHYS 240 -> Mon/Wed Slot 3, RH 204 [Direct Conflict]
                (15, 25): (["Tuesday", "Thursday"], 2, 5), # Dr. Hassan: ECE 216 -> Tue/Thu Slot 2, RH 211
                (16, 25): (["Tuesday", "Thursday"], 2, 5), # Dr. Chowdhury: ECE 216 -> Tue/Thu Slot 2, RH 211 [Direct Conflict]
                # Chem / Bio Conflicts:
                (17, 39): (["Tuesday", "Thursday"], 2, 1), # Dr. Kilway: CHEM 330 -> Tue/Thu Slot 2, SCB 101
                (19, 39): (["Tuesday", "Thursday"], 2, 1), # Dr. Moteki: CHEM 330 -> Tue/Thu Slot 2, SCB 101 [Direct Conflict]
                (18, 34): (["Monday", "Wednesday"], 4, 11),# Dr. Thomas: BIOL 109 -> Mon/Wed Slot 4, SCB 205 (lab)
                (20, 34): (["Monday", "Wednesday"], 4, 11),# Dr. Mohan: BIOL 109 -> Mon/Wed Slot 4, SCB 205 (lab) [Direct Conflict]
                (17, 40): (["Tuesday", "Thursday"], 4, 11),# CHEM 432 -> SCB 205 (lab)
                (20, 40): (["Tuesday", "Thursday"], 4, 9), # CHEM 432 -> FH 464 (lab)
            }
        else: # sem_id == 6: Spring 2027
            return {
                # CS Conflicts:
                (1, 13): (["Monday", "Wednesday"], 2, 3), # Dr. Lee: CS 461R -> Mon/Wed Slot 2, FH 256
                (2, 10): (["Monday", "Wednesday"], 2, 3), # Dr. Choi: CS 451R -> Mon/Wed Slot 2, FH 256 [Direct Conflict]
                (5, 10): (["Monday", "Wednesday"], 2, 3), # Dr. Song: CS 451R -> Mon/Wed Slot 2, FH 256 [Direct Conflict]
                (3, 16): (["Tuesday", "Thursday"], 3, 3), # Dr. Rao: CS 5560 -> Tue/Thu Slot 3, FH 256
                (4, 13): (["Tuesday", "Thursday"], 3, 3), # Dr. Derakhshani: CS 461R -> Tue/Thu Slot 3, FH 256 [Direct Conflict]
                (7, 12): (["Monday", "Wednesday"], 3, 9), # Dr. Tunc: CS 457 -> Mon/Wed Slot 3, FH 464 (lab)
                (4, 12): (["Monday", "Wednesday"], 3, 9), # Dr. Derakhshani: CS 457 -> Mon/Wed Slot 3, FH 464 (lab) [Direct Conflict]
                # Math Conflicts:
                (9, 17):  (["Monday", "Wednesday"], 3, 2),  # Dr. Bani-Yaghoub: MATH 110 -> Mon/Wed Slot 3, RH 204
                (12, 17): (["Monday", "Wednesday"], 3, 2), # Dr. Ge: MATH 110 -> Mon/Wed Slot 3, RH 204 [Direct Conflict]
                (10, 20): (["Tuesday", "Thursday"], 2, 4), # Dr. Rhee: MATH 300 -> Tue/Thu Slot 2, HH 301
                (11, 20): (["Tuesday", "Thursday"], 2, 4), # Dr. Sega: MATH 300 -> Tue/Thu Slot 2, HH 301 [Direct Conflict]
                # ECE / Phys Conflicts:
                (13, 31): (["Monday", "Wednesday"], 2, 2), # Dr. Caruso: PHYS 250 -> Mon/Wed Slot 2, RH 204
                (14, 31): (["Monday", "Wednesday"], 2, 2), # Dr. Chatterjee: PHYS 250 -> Mon/Wed Slot 2, RH 204 [Direct Conflict]
                (15, 27): (["Tuesday", "Thursday"], 4, 10),# Dr. Hassan: ECE 380 -> Tue/Thu Slot 4, FH 514 (lab)
                (16, 27): (["Tuesday", "Thursday"], 4, 10),# Dr. Chowdhury: ECE 380 -> Tue/Thu Slot 4, FH 514 (lab) [Direct Conflict]
                # Chem / Bio Conflicts:
                (17, 40): (["Monday", "Wednesday"], 4, 11),# Dr. Kilway: CHEM 432 -> Mon/Wed Slot 4, SCB 205 (lab)
                (20, 40): (["Monday", "Wednesday"], 4, 11),# Dr. Mohan: CHEM 432 -> Mon/Wed Slot 4, SCB 205 (lab) [Direct Conflict]
                (18, 35): (["Tuesday", "Thursday"], 2, 5), # Dr. Thomas: BIOL 302 -> Tue/Thu Slot 2, RH 211
                (20, 35): (["Tuesday", "Thursday"], 2, 5), # Dr. Mohan: BIOL 302 -> Tue/Thu Slot 2, RH 211 [Direct Conflict]
                (18, 34): (["Tuesday", "Thursday"], 4, 11),# BIOL 109 -> Tue/Thu Slot 4, SCB 205 (lab)
                (20, 34): (["Tuesday", "Thursday"], 4, 11)
            }

    preferences = []
    pref_id = 1
    for sem in semesters:
        sem_id = sem["id"]
        is_spring = (sem_id % 2 == 0)
        sem_conflicts = get_semester_conflicts(sem_id)

        for inst_id, c_list in sorted(qualifications.items()):
            inst_idx = inst_id - 1
            for i_course, c_id in enumerate(c_list):
                course_info = courses[c_id - 1]
                layout = course_info["required_layout"]
                enrollment = course_info["expected_enrollment"]

                # Check if this (instructor, course) pair has an explicit hotspot conflict in this semester
                if (inst_id, c_id) in sem_conflicts:
                    pref_days, slot_id, room_id = sem_conflicts[(inst_id, c_id)]
                    pref_slots = [slot_id]
                    matching_rooms = [r for r in rooms if r["room_id"] == room_id]
                    pref_room = matching_rooms[0] if matching_rooms else rooms[0]
                else:
                    # Day rotation: 17 out of 20 faculty alternate between Mon/Wed and Tue/Thu
                    # 12, 16, 20 maintain steady days
                    rotates = (inst_id not in [12, 16, 20])
                    if rotates:
                        if inst_id % 2 == 1:
                            pref_days = ["Monday", "Wednesday"] if is_spring else ["Tuesday", "Thursday"]
                        else:
                            pref_days = ["Tuesday", "Thursday"] if is_spring else ["Monday", "Wednesday"]
                    else:
                        pref_days = ["Tuesday", "Thursday"] if (inst_id % 2 == 1) else ["Monday", "Wednesday"]

                    # Slot variation: prime-time slots shift across semesters
                    slot_cycle = [2, 3, 4, 1]
                    slot_offset = (i_course + (sem_id - 1) + (inst_id % 3)) % len(slot_cycle)
                    slot_id = slot_cycle[slot_offset]
                    pref_slots = [slot_id]

                    # Select rooms from department-appropriate buildings:
                    if layout == "lab":
                        dept_bldgs = [1, 4] # All labs are in FH (1) and SCB (4)
                    elif c_id <= 16:
                        dept_bldgs = [1, 2, 5]
                    elif c_id <= 24:
                        dept_bldgs = [3, 2, 4] if enrollment > 100 else [3, 2]
                    elif c_id <= 32:
                        dept_bldgs = [1, 2]
                    else:
                        dept_bldgs = [4, 2]

                    matching_rooms = [
                        r for r in rooms
                        if r["building_id"] in dept_bldgs
                        and r["capacity"] >= enrollment
                        and (layout == "lecture" or r["layout_type"] == layout)
                    ]
                    if not matching_rooms:
                        matching_rooms = [r for r in rooms if r["capacity"] >= enrollment and (layout == "lecture" or r["layout_type"] == layout)]
                    if not matching_rooms:
                        matching_rooms = [r for r in rooms if r["capacity"] >= enrollment]

                    pref_room = matching_rooms[(inst_idx + i_course + sem_id) % len(matching_rooms)]

                preferences.append({
                    "id": pref_id,
                    "instructor_id": inst_id,
                    "course_id": c_id,
                    "preferred_days": pref_days,
                    "preferred_slot_id": slot_id,
                    "preferred_slots": pref_slots,
                    "preferred_room_id": pref_room["room_id"],
                    "preferred_layout": layout,
                    "semester_id": sem_id,
                    "exams_count": 2 if layout != "lab" else 1,
                    "has_final": (layout != "lab")
                })
                pref_id += 1

    # 9. Schedules (starts empty, populated upon solving)
    schedules = []

    # 10. Edit Requests (starts empty)
    edit_requests = []

    # Write all 10 tables to data/umkc/
    files = {
        "campuses.json": campuses,
        "buildings.json": buildings,
        "rooms.json": rooms,
        "time_slots.json": time_slots,
        "semesters.json": semesters,
        "users.json": users,
        "courses.json": courses,
        "instructor_preferences.json": preferences,
        "schedules.json": schedules,
        "edit_requests.json": edit_requests
    }

    for filename, data in files.items():
        path = os.path.join(OUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Generated {path} ({len(data)} records)")

    print(f"\n[Success] Generated UMKC dataset in {OUT_DIR}:")
    print(f"  - 2 Campuses")
    print(f"  - 5 Buildings")
    print(f"  - 12 Classrooms (capacities 25-150, 4 layout types)")
    print(f"  - 6 Daily Time Slots")
    print(f"  - 20 Instructors (8 CS, 4 Math, 4 ECE/Phys, 4 Chem/Bio)")
    print(f"  - 40 Courses (16 CS, 8 Math, 8 ECE/Phys, 8 Chem/Bio)")
    print(f"  - {len(preferences)} Qualification & Preference entries")


if __name__ == "__main__":
    generate_umkc_dataset()
