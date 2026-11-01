import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import html
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from ortools.sat.python import cp_model  # noqa: E402

from app.solver.data_loader import DataLoader  # noqa: E402
from app.solver.engine import (  # noqa: E402
    DATE,
    build_schedule_model,
    get_metadata,
    load_profiles_from_data,
)

DEFAULT_OUTPUT_DIR = os.path.join(_BACKEND_DIR, "data", "uiuc_foia")
RAW_FOIA_FILENAME = "stem_foia_headcounts_2016fa_2026sp.csv"
RAW_CATALOG_FILENAME = "stem_catalog_2021fa_2026sp.csv"

STEM_DEPTS: Tuple[str, ...] = ("CS", "ECE", "MATH", "STAT", "CHEM", "PHYS", "BIOE")

TERMS_20: Tuple[str, ...] = (
    "2016-fa",
    "2017-sp",
    "2017-fa",
    "2018-sp",
    "2018-fa",
    "2019-sp",
    "2019-fa",
    "2020-sp",
    "2020-fa",
    "2021-sp",
    "2021-fa",
    "2022-sp",
    "2022-fa",
    "2023-sp",
    "2023-fa",
    "2024-sp",
    "2024-fa",
    "2025-sp",
    "2025-fa",
    "2026-sp",
)

CATALOG_TERMS: Tuple[str, ...] = (
    "2021-fa",
    "2022-sp",
    "2022-fa",
    "2023-sp",
    "2023-fa",
    "2024-sp",
    "2024-fa",
    "2025-sp",
    "2025-fa",
    "2026-sp",
)

RAW_FOIA_HEADERS: Tuple[str, ...] = (
    "Year",
    "Term",
    "YearTerm",
    "Subject",
    "Number",
    "Course Title",
    "Sched Type",
    "Enrolled",
    "Primary Instructor",
)

RAW_CATALOG_HEADERS: Tuple[str, ...] = (
    "Year",
    "Term",
    "YearTerm",
    "Subject",
    "Number",
    "Name",
    "Credit Hours",
    "CRN",
    "Section",
    "Enrollment Status",
    "Type",
    "Type Code",
    "Start Time",
    "End Time",
    "Days of Week",
    "Room",
    "Building",
    "Instructors",
)

FORBIDDEN_GRADE_TOKENS = frozenset(
    {
        "A+",
        "A",
        "A-",
        "B+",
        "B",
        "B-",
        "C+",
        "C",
        "C-",
        "D+",
        "D",
        "D-",
        "F",
        "W",
        "GPA",
    }
)

ONLINE_OR_INDEPENDENT_TYPES = frozenset(
    {"ONL", "OLC", "OLB", "OD", "IND", "INT", "PKG", "CONF", "CNF"}
)

CAUSAL_2YR_LOOKBACK: Dict[int, Tuple[str, str, str, str]] = {
    1: ("2021-fa", "2022-sp", "2022-fa", "2023-sp"),
    2: ("2022-sp", "2022-fa", "2023-sp", "2023-fa"),
    3: ("2022-fa", "2023-sp", "2023-fa", "2024-sp"),
    4: ("2023-sp", "2023-fa", "2024-sp", "2024-fa"),
    5: ("2023-fa", "2024-sp", "2024-fa", "2025-sp"),
    6: ("2024-sp", "2024-fa", "2025-sp", "2025-fa"),
}

TIME_SLOTS: Tuple[Dict[str, Any], ...] = (
    {"slot_id": 1, "start_time": "08:00", "end_time": "09:15"},
    {"slot_id": 2, "start_time": "09:30", "end_time": "10:45"},
    {"slot_id": 3, "start_time": "11:00", "end_time": "12:15"},
    {"slot_id": 4, "start_time": "12:30", "end_time": "13:45"},
    {"slot_id": 5, "start_time": "14:00", "end_time": "15:15"},
    {"slot_id": 6, "start_time": "15:30", "end_time": "16:45"},
)

SLOT_START_MINUTES: Dict[int, int] = {
    1: 8 * 60,
    2: 9 * 60 + 30,
    3: 11 * 60,
    4: 12 * 60 + 30,
    5: 14 * 60,
    6: 15 * 60 + 30,
}

DAY_CHAR_TO_NAME: Tuple[Tuple[str, str], ...] = (
    ("M", "Monday"),
    ("T", "Tuesday"),
    ("W", "Wednesday"),
    ("R", "Thursday"),
    ("F", "Friday"),
)

_FIRST_NAME_EXPANSIONS: Dict[str, str] = {
    "Chandrasek": "Chandrasekhar",
}


@dataclass(frozen=True)
class BuildingSpec:
    building_id: int
    campus_id: int
    code: str
    name: str


@dataclass(frozen=True)
class RoomSpec:
    room_id: int
    room_number: str
    building_id: int
    campus_id: int
    capacity: int
    layout_type: str


@dataclass(frozen=True)
class FacultySpec:
    user_id: int
    ikey: Tuple[str, str]
    email: str
    department: str
    campus_id: int
    base_priority: int
    courses: Tuple[str, str]


@dataclass(frozen=True)
class SemesterSpec:
    semester_id: int
    year_term: str
    name: str
    start_date: str
    end_date: str
    is_active: bool


CAMPUSES: Tuple[Dict[str, Any], ...] = (
    {
        "campus_id": 1,
        "name": "UIUC Grainger Engineering Quad",
        "address": "1308 W Main St, Urbana, IL 61801",
    },
    {
        "campus_id": 2,
        "name": "UIUC Main Quad",
        "address": "601 E John St, Champaign, IL 61820",
    },
)

BUILDING_SPECS: Tuple[BuildingSpec, ...] = (
    BuildingSpec(1, 1, "SC", "Siebel Center for Comp Sci"),
    BuildingSpec(2, 1, "ECEB", "Electrical & Computer Eng Bldg"),
    BuildingSpec(3, 1, "CIF", "Campus Instructional Facility"),
    BuildingSpec(4, 1, "LL", "Loomis Laboratory"),
    BuildingSpec(5, 2, "NL", "Noyes Laboratory"),
    BuildingSpec(6, 1, "DCL", "Digital Computer Laboratory"),
    BuildingSpec(7, 1, "MSEB", "Materials Science & Eng Bld"),
)

BUILDING_NAME_TO_CODE: Dict[str, str] = {b.name: b.code for b in BUILDING_SPECS}

ROOM_SPECS: Tuple[RoomSpec, ...] = (
    RoomSpec(1, "NL 100", 5, 2, 322, "lecture"),
    RoomSpec(2, "LL 141", 4, 1, 278, "lecture"),
    RoomSpec(3, "CIF 35", 3, 1, 265, "lecture"),
    RoomSpec(4, "MSEB 100", 7, 1, 239, "lecture"),
    RoomSpec(5, "ECEB 1002", 2, 1, 228, "lecture"),
    RoomSpec(6, "DCL 1320", 6, 1, 205, "lecture"),
    RoomSpec(7, "SC 1404", 1, 1, 185, "lecture"),
    RoomSpec(8, "CIF 3031", 3, 1, 172, "lecture"),
    RoomSpec(9, "LL 151", 4, 1, 166, "lecture"),
    RoomSpec(10, "ECEB 2017", 2, 1, 136, "lecture"),
    RoomSpec(11, "ECEB 1013", 2, 1, 102, "lecture"),
    RoomSpec(12, "SC 216", 1, 1, 68, "lecture"),
    RoomSpec(13, "CIF 4031", 3, 1, 160, "lab"),
    RoomSpec(14, "ECEB 4074", 2, 1, 135, "lab"),
    RoomSpec(15, "LL 64", 4, 1, 112, "lab"),
    RoomSpec(16, "NL 204", 5, 2, 96, "lab"),
)

LAB_COURSES = frozenset(
    {
        ("CS", "461"),
        ("ECE", "206"),
        ("ECE", "311"),
        ("CHEM", "315"),
        ("BIOE", "202"),
    }
)

FACULTY_SPECS: Tuple[FacultySpec, ...] = (
    FacultySpec(
        1, ("lee", "h"), "leeh@illinois.edu", "STAT", 1, 115000, ("400", "429")
    ),
    FacultySpec(
        2, ("stepanov", "a"), "stepanov@illinois.edu", "STAT", 1, 112000, ("410", "420")
    ),
    FacultySpec(
        3, ("kinson", "c"), "kinson2@illinois.edu", "STAT", 1, 105000, ("385", "440")
    ),
    FacultySpec(
        4, ("ghose", "s"), "ghose@illinois.edu", "CS", 1, 108000, ("233", "433")
    ),
    FacultySpec(
        5, ("cunningham", "r"), "rcunning@illinois.edu", "CS", 1, 106000, ("210", "461")
    ),
    FacultySpec(
        6, ("borisov", "n"), "nikita@illinois.edu", "CS", 1, 114000, ("425", "438")
    ),
    FacultySpec(
        7, ("kloeckner", "a"), "andreask@illinois.edu", "CS", 1, 110000, ("357", "450")
    ),
    FacultySpec(
        8, ("bhowmik", "u"), "ubhowmik@illinois.edu", "ECE", 1, 108000, ("120", "220")
    ),
    FacultySpec(
        9,
        ("radhakrishnan", "c"),
        "cradhak@illinois.edu",
        "ECE",
        1,
        112000,
        ("206", "342"),
    ),
    FacultySpec(
        10, ("do", "m"), "minhdo@illinois.edu", "ECE", 1, 116000, ("310", "311")
    ),
    FacultySpec(
        11, ("schuh", "j"), "schuh4@illinois.edu", "ECE", 1, 104000, ("110", "330")
    ),
    FacultySpec(
        12, ("placzek", "l"), "lplaczek@illinois.edu", "MATH", 1, 105000, ("112", "115")
    ),
    FacultySpec(
        13,
        ("tzirakis", "n"),
        "tzirakis@illinois.edu",
        "MATH",
        1,
        110000,
        ("441", "442"),
    ),
    FacultySpec(
        14,
        ("nikolaev", "i"),
        "nikolaev@illinois.edu",
        "MATH",
        1,
        112000,
        ("444", "446"),
    ),
    FacultySpec(
        15, ("gewirth", "a"), "agewirth@illinois.edu", "CHEM", 2, 118000, ("312", "315")
    ),
    FacultySpec(
        16, ("burke", "m"), "mdburke@illinois.edu", "CHEM", 2, 116000, ("236", "237")
    ),
    FacultySpec(
        17, ("ansell", "k"), "ansellk@illinois.edu", "PHYS", 1, 106000, ("101", "102")
    ),
    FacultySpec(
        18, ("kou", "a"), "akou@illinois.edu", "PHYS", 1, 104000, ("435", "436")
    ),
    FacultySpec(
        19, ("jensen", "k"), "kjensen@illinois.edu", "BIOE", 1, 108000, ("120", "202")
    ),
    FacultySpec(
        20,
        ("dobrucki", "w"),
        "dobrucki@illinois.edu",
        "BIOE",
        1,
        110000,
        ("414", "498"),
    ),
)

CHRONOLOGICAL_SEMESTERS: Tuple[SemesterSpec, ...] = (
    SemesterSpec(101, "2016-fa", "Fall 2016", "2016-08-22", "2016-12-16", False),
    SemesterSpec(102, "2017-sp", "Spring 2017", "2017-01-17", "2017-05-12", False),
    SemesterSpec(103, "2017-fa", "Fall 2017", "2017-08-28", "2017-12-22", False),
    SemesterSpec(104, "2018-sp", "Spring 2018", "2018-01-16", "2018-05-11", False),
    SemesterSpec(105, "2018-fa", "Fall 2018", "2018-08-27", "2018-12-21", False),
    SemesterSpec(106, "2019-sp", "Spring 2019", "2019-01-14", "2019-05-10", False),
    SemesterSpec(107, "2019-fa", "Fall 2019", "2019-08-26", "2019-12-20", False),
    SemesterSpec(108, "2020-sp", "Spring 2020", "2020-01-21", "2020-05-15", False),
    SemesterSpec(109, "2020-fa", "Fall 2020", "2020-08-24", "2020-12-18", False),
    SemesterSpec(110, "2021-sp", "Spring 2021", "2021-01-25", "2021-05-14", False),
    SemesterSpec(111, "2021-fa", "Fall 2021", "2021-08-23", "2021-12-17", False),
    SemesterSpec(112, "2022-sp", "Spring 2022", "2022-01-18", "2022-05-13", False),
    SemesterSpec(113, "2022-fa", "Fall 2022", "2022-08-22", "2022-12-16", False),
    SemesterSpec(114, "2023-sp", "Spring 2023", "2023-01-17", "2023-05-12", False),
    SemesterSpec(1, "2023-fa", "Fall 2023", "2023-08-21", "2023-12-15", False),
    SemesterSpec(2, "2024-sp", "Spring 2024", "2024-01-16", "2024-05-10", False),
    SemesterSpec(3, "2024-fa", "Fall 2024", "2024-08-26", "2024-12-20", False),
    SemesterSpec(4, "2025-sp", "Spring 2025", "2025-01-21", "2025-05-16", False),
    SemesterSpec(5, "2025-fa", "Fall 2025", "2025-08-25", "2025-12-19", True),
    SemesterSpec(6, "2026-sp", "Spring 2026", "2026-01-20", "2026-05-15", False),
)


def normalize_instructor_key(raw_instructor: str) -> Optional[Tuple[str, str]]:
    if not raw_instructor or not raw_instructor.strip():
        return None
    primary = raw_instructor.split(";")[0].strip()
    if "," not in primary:
        return None
    last_part, first_part = primary.split(",", 1)
    last_norm = last_part.strip().lower()[:15]
    first_norm = first_part.strip()
    if not last_norm or not first_norm:
        return None
    return (last_norm, first_norm[0].lower())


def parse_clock_minutes(raw_time: str) -> Optional[int]:
    match = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", raw_time.strip(), re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(3).upper()
    if meridiem == "PM" and hour != 12:
        hour += 12
    elif meridiem == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute


def nearest_slot_id(start_minutes: int) -> int:
    return min(
        SLOT_START_MINUTES,
        key=lambda sid: (abs(SLOT_START_MINUTES[sid] - start_minutes), sid),
    )


def expand_weekdays(raw_days: str) -> Tuple[str, ...]:
    cleaned = raw_days.strip().upper()
    if not cleaned or cleaned == "ARR":
        return ()
    return tuple(name for code, name in DAY_CHAR_TO_NAME if code in cleaned)


def normalize_room_token(raw_room: str) -> str:
    token = raw_room.strip()
    if token.isdigit():
        return str(int(token))
    return token


def parse_credit_hours(raw_credits: str, default: int = 3) -> int:
    match = re.search(r"(\d+)", raw_credits or "")
    if not match:
        return default
    val = int(match.group(1))
    return val if 1 <= val <= 5 else default


def _assert_no_grade_headers(headers: Iterable[str], label: str) -> None:
    bad = [h for h in headers if h.strip().upper() in FORBIDDEN_GRADE_TOKENS]
    if bad:
        raise ValueError(f"Forbidden grade/GPA headers in {label}: {bad}")


def bootstrap_raw_snapshots(source_dir: str, raw_dir: str) -> None:
    os.makedirs(raw_dir, exist_ok=True)
    gpa_source = os.path.join(source_dir, "uiuc-gpa-dataset.csv")
    if not os.path.exists(gpa_source):
        raise FileNotFoundError(f"Missing FOIA source file: {gpa_source}")

    _assert_no_grade_headers(RAW_FOIA_HEADERS, RAW_FOIA_FILENAME)
    _assert_no_grade_headers(RAW_CATALOG_HEADERS, RAW_CATALOG_FILENAME)

    term_set = set(TERMS_20)
    dept_set = set(STEM_DEPTS)
    term_rank = {yt: idx for idx, yt in enumerate(TERMS_20)}

    foia_records: List[Tuple[str, ...]] = []
    with open(gpa_source, "r", encoding="cp1252", newline="") as handle:
        for row in csv.DictReader(handle):
            subj = row["Subject"].strip()
            yt = row["YearTerm"].strip()
            if subj not in dept_set or yt not in term_set:
                continue
            students = int(row["Students"].strip())
            w_raw = row["W"].strip()
            withdrawn = int(w_raw) if w_raw.isdigit() else 0
            enrolled = students + withdrawn
            foia_records.append(
                (
                    row["Year"].strip(),
                    row["Term"].strip(),
                    yt,
                    subj,
                    row["Number"].strip(),
                    row["Course Title"].strip(),
                    row["Sched Type"].strip(),
                    str(enrolled),
                    row["Primary Instructor"].strip(),
                )
            )

    foia_records.sort(
        key=lambda rec: (term_rank[rec[2]], rec[3], rec[4], rec[6], int(rec[7]), rec[8])
    )
    foia_out = os.path.join(raw_dir, RAW_FOIA_FILENAME)
    with open(foia_out, "w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(RAW_FOIA_HEADERS)
        writer.writerows(foia_records)

    cat_records: List[Tuple[str, ...]] = []
    for yt in CATALOG_TERMS:
        cat_path = os.path.join(source_dir, f"catalog-{yt}.csv")
        if not os.path.exists(cat_path):
            raise FileNotFoundError(f"Missing Catalog source file: {cat_path}")
        with open(cat_path, "r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                subj = row["Subject"].strip()
                if subj not in dept_set:
                    continue
                cat_records.append(
                    tuple(row[col].strip() for col in RAW_CATALOG_HEADERS)
                )

    cat_rank = {yt: idx for idx, yt in enumerate(CATALOG_TERMS)}
    cat_records.sort(
        key=lambda rec: (cat_rank[rec[2]], rec[3], rec[4], rec[7], rec[8])
    )
    cat_out = os.path.join(raw_dir, RAW_CATALOG_FILENAME)
    with open(cat_out, "w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(RAW_CATALOG_HEADERS)
        writer.writerows(cat_records)


def _read_raw_foia(raw_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(raw_dir, RAW_FOIA_FILENAME)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing raw FOIA snapshot {path}. Run with --bootstrap-from first."
        )
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _assert_no_grade_headers(reader.fieldnames or (), RAW_FOIA_FILENAME)
        for row in reader:
            rows.append(
                {
                    "year_term": row["YearTerm"].strip(),
                    "subject": row["Subject"].strip(),
                    "number": row["Number"].strip(),
                    "title": row["Course Title"].strip(),
                    "sched_type": row["Sched Type"].strip(),
                    "enrolled": int(row["Enrolled"].strip()),
                    "primary_instructor": row["Primary Instructor"].strip(),
                    "ikey": normalize_instructor_key(row["Primary Instructor"]),
                }
            )
    return rows


def _read_raw_catalog(raw_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(raw_dir, RAW_CATALOG_FILENAME)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing raw Catalog snapshot {path}. Run with --bootstrap-from first."
        )
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _assert_no_grade_headers(reader.fieldnames or (), RAW_CATALOG_FILENAME)
        for row in reader:
            rows.append(
                {
                    "year_term": row["YearTerm"].strip(),
                    "subject": row["Subject"].strip(),
                    "number": row["Number"].strip(),
                    "name": row["Name"].strip(),
                    "credit_hours": row["Credit Hours"].strip(),
                    "crn": row["CRN"].strip(),
                    "section": row["Section"].strip(),
                    "enrollment_status": row["Enrollment Status"].strip(),
                    "type_code": row["Type Code"].strip(),
                    "start_time": row["Start Time"].strip(),
                    "end_time": row["End Time"].strip(),
                    "days_of_week": row["Days of Week"].strip(),
                    "room": row["Room"].strip(),
                    "building": row["Building"].strip(),
                    "instructors": row["Instructors"].strip(),
                    "ikey": normalize_instructor_key(row["Instructors"]),
                }
            )
    return rows


def _reconstruct_faculty_name(
    spec: FacultySpec,
    foia_rows: Sequence[Dict[str, Any]],
    catalog_rows: Sequence[Dict[str, Any]],
) -> str:
    dept_hits = Counter(
        r["primary_instructor"]
        for r in foia_rows
        if r["ikey"] == spec.ikey and r["subject"] == spec.department
    )
    if not dept_hits:
        dept_hits = Counter(
            r["primary_instructor"] for r in foia_rows if r["ikey"] == spec.ikey
        )
    modal_raw = sorted(dept_hits.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    last_raw, rest_raw = modal_raw.split(",", 1)
    first_token = rest_raw.strip().split()[0]
    first_full = _FIRST_NAME_EXPANSIONS.get(first_token, first_token)
    last_full = last_raw.strip()

    cat_last_hits = Counter(
        r["instructors"].split(";")[0].split(",")[0].strip()
        for r in catalog_rows
        if r["ikey"] == spec.ikey
        and r["subject"] == spec.department
        and "," in r["instructors"].split(";")[0]
    )
    if cat_last_hits:
        cand_last = sorted(cat_last_hits.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        if len(cand_last) > len(last_full) and cand_last.lower().startswith(
            last_full.lower()[:14]
        ):
            last_full = cand_last
    return f"Dr. {first_full} {last_full}"


def _single_section_headcount(
    term_rows: Sequence[Dict[str, Any]],
    assigned_ikey: Tuple[str, str],
) -> int:
    own_valid = [
        r["enrolled"]
        for r in term_rows
        if r["ikey"] == assigned_ikey and 21 <= r["enrolled"] <= 240
    ]
    if len(own_valid) == 1:
        return own_valid[0]

    in_person = [
        r["enrolled"]
        for r in term_rows
        if r["sched_type"] not in ONLINE_OR_INDEPENDENT_TYPES and r["enrolled"] >= 21
    ]
    pool = in_person if in_person else [r["enrolled"] for r in term_rows]
    mean_val = round(sum(pool) / len(pool))
    return min(240, max(21, mean_val))


def _build_course_series(
    foia_by_term: Dict[str, List[Dict[str, Any]]],
    assigned_ikey: Tuple[str, str],
) -> Dict[str, int]:
    observed: Dict[str, int] = {}
    for yt in TERMS_20:
        rows = foia_by_term.get(yt)
        if rows:
            observed[yt] = _single_section_headcount(rows, assigned_ikey)

    complete: Dict[str, int] = {}
    for idx, yt in enumerate(TERMS_20):
        if yt in observed:
            complete[yt] = observed[yt]
            continue
        season = yt.split("-")[1]
        same_season = [
            (abs(idx - j), j, TERMS_20[j])
            for j in range(len(TERMS_20))
            if TERMS_20[j] in observed
            and TERMS_20[j].endswith(season)
            and TERMS_20[j] != "2026-sp"
        ]
        if not same_season:
            raise ValueError(f"No same-season FOIA observation to fill {yt}")
        same_season.sort()
        complete[yt] = observed[same_season[0][2]]
    return complete


def _resolve_clean_title(
    subject: str,
    number: str,
    foia_rows: Sequence[Dict[str, Any]],
    catalog_rows: Sequence[Dict[str, Any]],
) -> str:
    cat_names = Counter(
        r["name"]
        for r in catalog_rows
        if r["subject"] == subject and r["number"] == number and r["name"]
    )
    foia_titles = Counter(
        r["title"]
        for r in foia_rows
        if r["subject"] == subject and r["number"] == number and r["title"]
    )
    chosen = ""
    if cat_names:
        cand = sorted(cat_names.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        if "special topics" not in cand.lower():
            chosen = cand
    if not chosen and foia_titles:
        chosen = sorted(foia_titles.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    cleaned = re.sub(r"\s+", " ", html.unescape(chosen)).strip()
    return f"{subject} {number} {cleaned}"


def _build_preferences(
    assignments: Sequence[Tuple[int, Tuple[str, str], Dict[str, Any]]],
    catalog_rows: Sequence[Dict[str, Any]],
    rooms: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    room_lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for rm in rooms:
        bcode, rnum = rm["room_number"].split(" ", 1)
        room_lookup[(bcode, normalize_room_token(rnum))] = rm

    cat_index: Dict[Tuple[Tuple[str, str], str, str], List[Dict[str, Any]]] = (
        defaultdict(list)
    )
    for row in catalog_rows:
        if row["year_term"] == "2026-sp" or row["ikey"] is None:
            continue
        if row["type_code"] in ONLINE_OR_INDEPENDENT_TYPES:
            continue
        if not row["building"] or not row["room"] or row["room"] == "ARR":
            continue
        days = expand_weekdays(row["days_of_week"])
        mins = parse_clock_minutes(row["start_time"])
        if not days or mins is None:
            continue
        enriched = dict(row)
        enriched["expanded_days"] = days
        enriched["slot_id"] = nearest_slot_id(mins)
        cat_index[(row["ikey"], row["subject"], row["number"])].append(enriched)

    preferences: List[Dict[str, Any]] = []
    pref_id = 1
    for sem_id in range(1, 7):
        window = CAUSAL_2YR_LOOKBACK[sem_id]
        term_order = {yt: idx for idx, yt in enumerate(window)}
        for instructor_id, ikey, course in assignments:
            subj, num = course["course_name"].split()[:2]
            hits = [
                r
                for r in cat_index.get((ikey, subj, num), ())
                if r["year_term"] in term_order
            ]
            multi_day_hits = [r for r in hits if len(r["expanded_days"]) >= 2]
            pool = multi_day_hits if multi_day_hits else hits

            if not pool:
                preferences.append(
                    {
                        "id": pref_id,
                        "instructor_id": instructor_id,
                        "course_id": course["course_id"],
                        "preferred_days": [],
                        "preferred_slot_id": None,
                        "preferred_slots": [],
                        "preferred_room_id": None,
                        "preferred_layout": None,
                        "semester_id": sem_id,
                        "exams_count": 2,
                        "has_final": True,
                    }
                )
                pref_id += 1
                continue

            pattern_counts: Counter = Counter()
            pattern_latest: Dict[Tuple[Tuple[str, ...], int], int] = {}
            for r in pool:
                key = (r["expanded_days"], int(r["slot_id"]))
                pattern_counts[key] += 1
                t_idx = term_order[r["year_term"]]
                if t_idx > pattern_latest.get(key, -1):
                    pattern_latest[key] = t_idx

            best_days, best_slot = max(
                pattern_counts,
                key=lambda k: (pattern_counts[k], pattern_latest[k], -k[1], k[0]),
            )

            room_counts: Counter = Counter()
            room_latest: Dict[int, int] = {}
            for r in hits:
                bcode = BUILDING_NAME_TO_CODE.get(r["building"])
                if not bcode:
                    continue
                cand_room = room_lookup.get((bcode, normalize_room_token(r["room"])))
                if cand_room is None:
                    continue
                if cand_room["capacity"] < course["expected_enrollment"]:
                    continue
                if (
                    course["required_layout"] == "lab"
                    and cand_room["layout_type"] != "lab"
                ):
                    continue
                rid = int(cand_room["room_id"])
                weight = (
                    2
                    if (r["expanded_days"], int(r["slot_id"]))
                    == (best_days, best_slot)
                    else 1
                )
                room_counts[rid] += weight
                t_idx = term_order[r["year_term"]]
                if t_idx > room_latest.get(rid, -1):
                    room_latest[rid] = t_idx

            best_room_id: Optional[int] = None
            if room_counts:
                best_room_id = max(
                    room_counts,
                    key=lambda rid: (room_counts[rid], room_latest[rid], -rid),
                )

            preferences.append(
                {
                    "id": pref_id,
                    "instructor_id": instructor_id,
                    "course_id": course["course_id"],
                    "preferred_days": list(best_days),
                    "preferred_slot_id": best_slot,
                    "preferred_slots": [best_slot],
                    "preferred_room_id": best_room_id,
                    "preferred_layout": course["required_layout"],
                    "semester_id": sem_id,
                    "exams_count": 2,
                    "has_final": True,
                }
            )
            pref_id += 1

    return preferences


def _build_heldout_ground_truth(
    assignments: Sequence[Tuple[int, Tuple[str, str], Dict[str, Any]]],
    users_by_id: Dict[int, Dict[str, Any]],
    series_by_course_id: Dict[int, Dict[str, int]],
    preferences: Sequence[Dict[str, Any]],
    foia_rows: Sequence[Dict[str, Any]],
    catalog_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    foia_by_ct: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in foia_rows:
        foia_by_ct[(r["subject"], r["number"], r["year_term"])].append(r)

    historical_room_cap: Dict[Tuple[str, str], int] = defaultdict(int)
    for r in catalog_rows:
        if r["year_term"] == "2026-sp":
            continue
        bldg = r["building"]
        rm = normalize_room_token(r["room"])
        if not bldg or not rm or rm == "ARR":
            continue
        f_rows = foia_by_ct.get((r["subject"], r["number"], r["year_term"]), [])
        if not f_rows:
            continue
        matched = [
            x["enrolled"]
            for x in f_rows
            if x["ikey"] == r["ikey"] and r["ikey"] is not None
        ]
        if len(matched) == 1 and matched[0] <= 450:
            sec_enr: Optional[int] = matched[0]
        elif r["type_code"] in ("LEC", "LCD"):
            avg = round(sum(x["enrolled"] for x in f_rows) / len(f_rows))
            sec_enr = avg if avg <= 450 else None
        else:
            sec_enr = None
        if sec_enr is not None and r["type_code"] in ("LEC", "LCD"):
            key = (bldg, rm)
            if sec_enr > historical_room_cap[key]:
                historical_room_cap[key] = sec_enr

    for room_spec in ROOM_SPECS:
        bcode, rnum = room_spec.room_number.split(" ", 1)
        bname = next(b.name for b in BUILDING_SPECS if b.code == bcode)
        key = (bname, normalize_room_token(rnum))
        if room_spec.capacity > historical_room_cap[key]:
            historical_room_cap[key] = room_spec.capacity

    eval_utils: List[float] = []
    total_seats = 0
    total_enrolled = 0
    over_50_empty = 0
    midday_count = 0
    timed_count = 0

    for r in catalog_rows:
        if r["year_term"] != "2026-sp" or r["type_code"] not in ("LEC", "LCD"):
            continue
        bldg = r["building"]
        rm = normalize_room_token(r["room"])
        if not bldg or not rm or rm == "ARR":
            continue
        mins = parse_clock_minutes(r["start_time"])
        if mins is not None:
            timed_count += 1
            if 600 <= mins < 840:
                midday_count += 1
        cap = historical_room_cap.get((bldg, rm), 0)
        f_rows = foia_by_ct.get((r["subject"], r["number"], "2026-sp"), [])
        matched = [
            x["enrolled"]
            for x in f_rows
            if x["ikey"] == r["ikey"] and r["ikey"] is not None
        ]
        if len(matched) == 1 and matched[0] <= 450:
            sec_enr = matched[0]
        elif f_rows:
            avg = round(sum(x["enrolled"] for x in f_rows) / len(f_rows))
            sec_enr = avg if avg <= 450 else None
        else:
            sec_enr = None
        if cap >= 25 and sec_enr is not None and sec_enr <= cap:
            util = sec_enr / cap
            eval_utils.append(util)
            total_seats += cap
            total_enrolled += sec_enr
            if util < 0.5:
                over_50_empty += 1

    pref_sem6 = {
        (p["instructor_id"], p["course_id"]): bool(
            p["preferred_days"] or p["preferred_slots"] or p["preferred_room_id"]
        )
        for p in preferences
        if p["semester_id"] == 6
    }

    cat_26sp_by_course: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in catalog_rows:
        if r["year_term"] == "2026-sp":
            cat_26sp_by_course[(r["subject"], r["number"])].append(r)

    type_priority = {"LEC": 0, "LCD": 1, "LBD": 2, "LAB": 3, "DIS": 4}
    course_entries: List[Dict[str, Any]] = []
    for instructor_id, ikey, course in assignments:
        cid = int(course["course_id"])
        subj, num = course["course_name"].split()[:2]
        code = f"{subj} {num}"
        series = series_by_course_id[cid]
        cands = [
            r
            for r in cat_26sp_by_course.get((subj, num), [])
            if r["type_code"] not in ONLINE_OR_INDEPENDENT_TYPES
            and r["building"]
            and r["room"]
            and r["room"] != "ARR"
        ]
        cands.sort(
            key=lambda r: (
                0 if r["ikey"] == ikey else 1,
                type_priority.get(r["type_code"], 9),
                r["section"],
            )
        )
        chosen = cands[0] if cands else None
        actual_bldg = chosen["building"] if chosen else None
        actual_room = chosen["room"] if chosen else None
        actual_cap = (
            historical_room_cap.get(
                (actual_bldg, normalize_room_token(actual_room)), None
            )
            if actual_bldg and actual_room
            else None
        )
        if actual_cap is not None and actual_cap < series["2026-sp"]:
            actual_cap = series["2026-sp"]

        course_entries.append(
            {
                "course_id": cid,
                "course_code": code,
                "course_name": course["course_name"],
                "department": subj,
                "instructor_id": instructor_id,
                "instructor_name": users_by_id[instructor_id]["name"],
                "has_2yr_preference": pref_sem6[(instructor_id, cid)],
                "fall_2025_enrolled": series["2025-fa"],
                "spring_2025_enrolled": series["2025-sp"],
                "actual_spring_2026_enrolled": series["2026-sp"],
                "uiuc_actual_building": actual_bldg,
                "uiuc_actual_room": actual_room,
                "uiuc_actual_room_capacity": actual_cap,
                "uiuc_actual_days": chosen["days_of_week"] if chosen else None,
                "uiuc_actual_start_time": chosen["start_time"] if chosen else None,
                "uiuc_actual_end_time": chosen["end_time"] if chosen else None,
                "uiuc_actual_enrollment_status": (
                    chosen["enrollment_status"] if chosen else None
                ),
            }
        )

    return {
        "heldout_term": "2026-sp",
        "heldout_semester_id": 6,
        "heldout_semester_name": "Spring 2026",
        "campus_wide_2026sp_audit": {
            "evaluated_sections": len(eval_utils),
            "mean_seat_utilization_pct": round(
                sum(eval_utils) / max(len(eval_utils), 1) * 100.0, 2
            ),
            "empty_seat_waste_pct": round(
                (1.0 - total_enrolled / max(total_seats, 1)) * 100.0, 2
            ),
            "oversized_over_50pct_empty_count": over_50_empty,
            "midday_10am_2pm_concentration_pct": round(
                midday_count / max(timed_count, 1) * 100.0, 2
            ),
        },
        "courses": course_entries,
    }


def _solve_semester_schedule(
    loader: DataLoader, semester_id: int, seed: int = 42
) -> List[Dict[str, Any]]:
    profiles = load_profiles_from_data(loader, semester_id=semester_id)
    slots = loader.get_slots_dict()
    class_room = [r["room_number"] for r in loader.rooms]
    instructors = [u["name"] for u in loader.get_instructors()]
    courses = [c["course_name"] for c in loader.courses]
    room_caps, course_enrolls, room_layouts = get_metadata(loader)
    valid_ic = sorted(loader.get_valid_ic_pairs())
    valid_rc = loader.get_valid_rc_pairs()

    model, x_vars, y_vars, z_vars, _ = build_schedule_model(
        profiles,
        DATE,
        class_room,
        instructors,
        courses,
        slots,
        seed=seed,
        room_capacities=room_caps,
        course_enrollments=course_enrolls,
        room_layouts=room_layouts,
        valid_ic_pairs=valid_ic,
        valid_rc_pairs=valid_rc,
        min_courses_per_instructor=1,
        max_courses_per_instructor=2,
    )

    obj_proto = model.Proto().objective
    if len(obj_proto.vars) > 1:
        paired = sorted(zip(obj_proto.vars, obj_proto.coeffs))
        obj_proto.vars.clear()
        obj_proto.coeffs.clear()
        obj_proto.vars.extend([int(v) for v, _ in paired])
        obj_proto.coeffs.extend([int(c) for _, c in paired])

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = seed
    solver.parameters.num_workers = 1
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)
    if status != cp_model.OPTIMAL:
        raise RuntimeError(
            f"Expected OPTIMAL CP-SAT schedule for semester {semester_id}, got {status}"
        )

    inst_name_to_id = {u["name"]: u["user_id"] for u in loader.get_instructors()}
    course_name_to_id = {c["course_name"]: c["course_id"] for c in loader.courses}
    room_number_to_id = {r["room_number"]: r["room_id"] for r in loader.rooms}

    schedules_list: List[Dict[str, Any]] = []
    occupied_room_day_slot = set()
    occupied_inst_day_slot = set()
    schedule_id = 1

    for c_name in courses:
        for i_name in instructors:
            if (
                (i_name, c_name) not in z_vars
                or solver.Value(z_vars[i_name, c_name]) != 1
            ):
                continue
            assigned_room: Optional[str] = None
            assigned_slot: Optional[int] = None
            for r_num in class_room:
                for s_id in sorted(slots):
                    if (r_num, s_id, i_name, c_name) in y_vars and solver.Value(
                        y_vars[r_num, s_id, i_name, c_name]
                    ) == 1:
                        assigned_room = r_num
                        assigned_slot = int(s_id)
                        break
                if assigned_room is not None:
                    break
            if assigned_room is None or assigned_slot is None:
                raise RuntimeError(
                    f"Unplaced course {c_name} in semester {semester_id}"
                )

            assigned_days = [
                d
                for d in DATE
                if (d, assigned_room, assigned_slot, i_name, c_name) in x_vars
                and solver.Value(
                    x_vars[d, assigned_room, assigned_slot, i_name, c_name]
                )
                == 1
            ]
            for day_name in assigned_days:
                rk = (assigned_room, day_name, assigned_slot)
                ik = (i_name, day_name, assigned_slot)
                if rk in occupied_room_day_slot or ik in occupied_inst_day_slot:
                    raise RuntimeError(f"Conflict detected in semester {semester_id}")
                occupied_room_day_slot.add(rk)
                occupied_inst_day_slot.add(ik)

            schedules_list.append(
                {
                    "schedule_id": schedule_id,
                    "course_id": course_name_to_id[c_name],
                    "course_name": c_name,
                    "instructor_id": inst_name_to_id[i_name],
                    "instructor_name": i_name,
                    "room_id": room_number_to_id[assigned_room],
                    "room_number": assigned_room,
                    "slot_id": assigned_slot,
                    "days": "/".join(assigned_days),
                    "semester_id": semester_id,
                    "status": "confirmed",
                }
            )
            schedule_id += 1

    if len(schedules_list) != len(courses):
        raise RuntimeError(
            f"Expected {len(courses)} scheduled courses, got {len(schedules_list)}"
        )
    return schedules_list


def _write_json(output_dir: str, filename: str, payload: Any) -> None:
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def build_dataset(output_dir: str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    raw_dir = os.path.join(output_dir, "raw")
    foia_rows = _read_raw_foia(raw_dir)
    catalog_rows = _read_raw_catalog(raw_dir)

    os.makedirs(output_dir, exist_ok=True)

    buildings = [
        {
            "building_id": b.building_id,
            "campus_id": b.campus_id,
            "name": b.name,
            "code": b.code,
        }
        for b in BUILDING_SPECS
    ]
    rooms = [
        {
            "room_id": r.room_id,
            "room_number": r.room_number,
            "building_id": r.building_id,
            "campus_id": r.campus_id,
            "capacity": r.capacity,
            "layout_type": r.layout_type,
        }
        for r in ROOM_SPECS
    ]

    users: List[Dict[str, Any]] = []
    for spec in FACULTY_SPECS:
        full_name = _reconstruct_faculty_name(spec, foia_rows, catalog_rows)
        users.append(
            {
                "user_id": spec.user_id,
                "name": full_name,
                "email": spec.email,
                "department": spec.department,
                "role": "instructor",
                "campus_id": spec.campus_id,
                "base_priority": spec.base_priority,
                "priority_points": spec.base_priority,
            }
        )
    users_by_id = {u["user_id"]: u for u in users}

    foia_index: Dict[Tuple[str, str], Dict[str, List[Dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in foia_rows:
        foia_index[(r["subject"], r["number"])][r["year_term"]].append(r)

    credits_index: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    for r in catalog_rows:
        if r["credit_hours"]:
            credits_index[(r["subject"], r["number"])][
                parse_credit_hours(r["credit_hours"])
            ] += 1

    courses: List[Dict[str, Any]] = []
    assignments: List[Tuple[int, Tuple[str, str], Dict[str, Any]]] = []
    series_by_course_id: Dict[int, Dict[str, int]] = {}
    course_id = 1

    for spec in FACULTY_SPECS:
        for num in spec.courses:
            key = (spec.department, num)
            series = _build_course_series(foia_index[key], spec.ikey)
            series_by_course_id[course_id] = series
            cred_counter = credits_index.get(key)
            credits = (
                sorted(cred_counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                if cred_counter
                else 3
            )
            course_obj = {
                "course_id": course_id,
                "course_name": _resolve_clean_title(
                    spec.department, num, foia_rows, catalog_rows
                ),
                "expected_enrollment": series["2025-fa"],
                "required_layout": "lab" if key in LAB_COURSES else "lecture",
                "credits": credits,
            }
            courses.append(course_obj)
            assignments.append((spec.user_id, spec.ikey, course_obj))
            course_id += 1

    semesters_sorted = sorted(CHRONOLOGICAL_SEMESTERS, key=lambda s: s.semester_id)
    semesters = [
        {
            "semester_id": s.semester_id,
            "id": s.semester_id,
            "name": s.name,
            "start_date": s.start_date,
            "end_date": s.end_date,
            "is_active": s.is_active,
        }
        for s in semesters_sorted
    ]

    observed_semesters = [
        s for s in CHRONOLOGICAL_SEMESTERS if s.semester_id != 6
    ]
    enrollment_history: List[Dict[str, Any]] = []
    for c_obj in courses:
        cid = int(c_obj["course_id"])
        series = series_by_course_id[cid]
        for sem_spec in observed_semesters:
            enrollment_history.append(
                {
                    "course_id": cid,
                    "semester_id": sem_spec.semester_id,
                    "enrolled": series[sem_spec.year_term],
                    "waitlist": 0,
                    "source": "uiuc_foia_registrar",
                }
            )

    preferences = _build_preferences(assignments, catalog_rows, rooms)
    heldout = _build_heldout_ground_truth(
        assignments,
        users_by_id,
        series_by_course_id,
        preferences,
        foia_rows,
        catalog_rows,
    )

    _write_json(output_dir, "campuses.json", list(CAMPUSES))
    _write_json(output_dir, "buildings.json", buildings)
    _write_json(output_dir, "rooms.json", rooms)
    _write_json(output_dir, "users.json", users)
    _write_json(output_dir, "courses.json", courses)
    _write_json(output_dir, "time_slots.json", list(TIME_SLOTS))
    _write_json(output_dir, "semesters.json", semesters)
    _write_json(output_dir, "instructor_preferences.json", preferences)
    _write_json(output_dir, "enrollment_history.json", enrollment_history)
    _write_json(output_dir, "edit_requests.json", [])
    _write_json(output_dir, "heldout_spring2026_ground_truth.json", heldout)

    loader = DataLoader(data_dir=output_dir)
    ok, errors = loader.validate_integrity()
    if not ok:
        raise RuntimeError(f"Relational integrity validation failed: {errors}")

    schedules_by_sem: Dict[int, List[Dict[str, Any]]] = {}
    for sem_id in range(1, 7):
        solved = _solve_semester_schedule(loader, semester_id=sem_id, seed=42)
        schedules_by_sem[sem_id] = solved
        _write_json(output_dir, f"schedules_sem{sem_id}.json", solved)

    _write_json(output_dir, "schedules.json", schedules_by_sem[5])

    return {
        "courses": len(courses),
        "users": len(users),
        "rooms": len(rooms),
        "semesters": len(semesters),
        "enrollment_history": len(enrollment_history),
        "preferences": len(preferences),
        "sem6_with_2yr_pref": sum(
            1 for c in heldout["courses"] if c["has_2yr_preference"]
        ),
        "sem6_without_2yr_pref": sum(
            1 for c in heldout["courses"] if not c["has_2yr_preference"]
        ),
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic UIUC FOIA + Course Explorer dataset profile."
    )
    parser.add_argument(
        "--bootstrap-from",
        dest="bootstrap_from",
        default=None,
        help="Optional directory containing full UIUC FOIA & Catalog CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Target output directory (defaults to backend/data/uiuc_foia).",
    )
    args = parser.parse_args(argv)

    output_dir = os.path.abspath(args.output_dir)
    if args.bootstrap_from:
        bootstrap_raw_snapshots(
            os.path.abspath(args.bootstrap_from), os.path.join(output_dir, "raw")
        )

    summary = build_dataset(output_dir=output_dir)
    print("Built uiuc_foia dataset:", json.dumps(summary))


if __name__ == "__main__":
    main()
