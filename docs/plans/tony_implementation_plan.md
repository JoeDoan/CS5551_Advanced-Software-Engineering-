# Sprint 1 Individual Implementation Plan: Tony Nguyen

**Name:** Tony Nguyen  
**Role:** Backend Lead Engineer (REST APIs, Data Schemas, Database CRUD)  
**Assigned User Stories:** US-3, US-4, US-5  
**Assigned Acceptance Criteria:** AC 3.1, AC 3.2, AC 3.3, AC 3.4, AC 4.1, AC 4.2, AC 4.3, AC 5.1, AC 5.2  
**Target LOC:** 680+ Lines of Code (Production + Automated Tests)  
**Branch:** `feature/tony-crud-apis-validation`  

---

## 1. Domain Ownership & Responsibilities

In Sprint 0, Tony established the initial FastAPI boilerplate, SQLModel entity models (`entities.py`), and draft OpenAPI specifications.  
In **Sprint 1**, Tony's primary objective is to deliver **full, robust REST CRUD APIs with rigorous Pydantic validation and error handling**:
1. Implement complete CRUD for **Courses** (Create, Read with filtering, Update, Delete with cascade protection).
2. Implement complete CRUD for **Rooms** (Capacity boundaries, lab room type validation, building association).
3. Implement **Instructor Preferences** retrieval and submission endpoints.
4. Author comprehensive Pydantic schemas in `api_schemas.py` enforcing field constraints (e.g., positive capacity, valid course codes, enum room types).
5. Author a rigorous Pytest test suite covering valid requests, 404 Not Found, 409 Conflict (duplicate codes), and 422 Unprocessable Entity.

---

## 2. Step-by-Step Task Checklist

```
[ ] Step 1: Create Git Branch 'feature/tony-crud-apis-validation'
[ ] Step 2: Expand Pydantic Schemas ('backend/app/schemas/api_schemas.py')
[ ] Step 3: Implement Course CRUD Router ('backend/app/api/v1/routes_courses.py')
[ ] Step 4: Implement Room CRUD Router ('backend/app/api/v1/routes_rooms.py')
[ ] Step 5: Implement Preference Router ('backend/app/api/v1/routes_preferences.py')
[ ] Step 6: Mount Sub-routers into 'backend/app/api/v1/routes.py' or 'main.py'
[ ] Step 7: Author Automated Pytest Suites ('test_courses_api.py', 'test_rooms_api.py', 'test_preferences_api.py')
[ ] Step 8: Verify 100% Test Pass Rate & Run Test Coverage
[ ] Step 9: Prepare Segment 2 for 5-Minute Demonstration Video
```

---

## 3. Detailed Technical Implementation

### Task 1: Pydantic Validation Schemas (`backend/app/schemas/api_schemas.py`)
* **File Location:** `backend/app/schemas/api_schemas.py` (~90 LOC addition)
* **Schemas to add/expand:**
  ```python
  from pydantic import BaseModel, Field
  from typing import Optional, List

  class CourseCreate(BaseModel):
      course_code: str = Field(..., min_length=3, max_length=15, example="CS 451")
      course_name: str = Field(..., min_length=2, max_length=100)
      department: str = Field(..., example="CS")
      credits: int = Field(default=3, ge=1, le=6)
      expected_enrollment: int = Field(default=30, ge=1, le=500)
      requires_lab: bool = False

  class CourseUpdate(BaseModel):
      course_name: Optional[str] = None
      department: Optional[str] = None
      credits: Optional[int] = Field(default=None, ge=1, le=6)
      expected_enrollment: Optional[int] = Field(default=None, ge=1, le=500)
      requires_lab: Optional[bool] = None

  class RoomCreate(BaseModel):
      building_id: int
      room_number: str = Field(..., min_length=1, max_length=20)
      capacity: int = Field(..., ge=1, le=600, description="Room capacity must be positive")
      room_type: str = Field(default="lecture", pattern="^(lecture|lab|seminar)$")

  class RoomUpdate(BaseModel):
      capacity: Optional[int] = Field(default=None, ge=1, le=600)
      room_type: Optional[str] = Field(default=None, pattern="^(lecture|lab|seminar)$")
  ```

### Task 2: Course CRUD Router (`backend/app/api/v1/routes_courses.py`)
* **File Location:** `backend/app/api/v1/routes_courses.py` (~140 LOC)
* **Endpoints:**
  * `POST /api/v1/courses`: Checks if `course_code` exists. If exists, raises `HTTPException(409, "Course code already exists")`. Otherwise inserts and returns `201 Created`. (Satisfies **AC 3.1, AC 3.2**).
  * `GET /api/v1/courses`: Supports `?department=CS&search=software`. Returns `200 OK` list. (Satisfies **AC 3.3**).
  * `GET /api/v1/courses/{id}`: Returns course or `404 Not Found`.
  * `PUT /api/v1/courses/{id}`: Updates fields. Returns updated course or `404`. (Satisfies **AC 3.4**).
  * `DELETE /api/v1/courses/{id}`: Deletes course. Returns `204 No Content`. (Satisfies **AC 3.4**).

### Task 3: Room CRUD Router (`backend/app/api/v1/routes_rooms.py`)
* **File Location:** `backend/app/api/v1/routes_rooms.py` (~130 LOC)
* **Endpoints:**
  * `POST /api/v1/rooms`: Creates room; validates building exists. Returns `201 Created`. (Satisfies **AC 4.1, AC 4.2**).
  * `GET /api/v1/rooms`: Filter by `?min_capacity=50&room_type=lecture`. Returns `200 OK`. (Satisfies **AC 4.3**).
  * `GET /api/v1/rooms/{id}`: Returns room details.
  * `PUT /api/v1/rooms/{id}`: Updates capacity/type.
  * `DELETE /api/v1/rooms/{id}`: Deletes room. Returns `204`.

### Task 4: Instructor Preference Router (`backend/app/api/v1/routes_preferences.py`)
* **File Location:** `backend/app/api/v1/routes_preferences.py` (~100 LOC)
* **Endpoints:**
  * `POST /api/v1/preferences`: Submits preferences (validates instructor and semester exist). Returns `201 Created`. (Satisfies **AC 5.1**).
  * `GET /api/v1/preferences`: Query by `?user_id=1&semester_id=1`. Returns list of saved preferences. (Satisfies **AC 5.2**).
  * `DELETE /api/v1/preferences/{id}`: Deletes a preference entry. Returns `204`.

### Task 5: Automated Pytest Suite
* **Files to Create:**
  * `backend/tests/test_courses_api.py` (~130 LOC)
    * `test_create_course_success()` (HTTP 201)
    * `test_create_course_duplicate_conflict()` (HTTP 409)
    * `test_create_course_invalid_enrollment()` (HTTP 422)
    * `test_filter_courses_by_department()`
    * `test_update_course()` (HTTP 200)
    * `test_delete_course_and_get_404()` (HTTP 204 then 404)
  * `backend/tests/test_rooms_api.py` (~110 LOC)
    * `test_create_room_success()`
    * `test_create_room_negative_capacity_fails()` (HTTP 422)
    * `test_filter_rooms_by_capacity_and_type()`
    * `test_delete_room()`
  * `backend/tests/test_preferences_api.py` (~100 LOC)
    * `test_submit_preference_success()`
    * `test_get_preferences_by_user_id()`
    * `test_preference_nonexistent_user_fails()`

---

## 4. LOC Contribution Breakdown for Tony

| File | Type | Purpose | LOC Estimate |
| :--- | :--- | :--- | :---: |
| `backend/app/schemas/api_schemas.py` | Production | Request/Response Pydantic validation schemas | ~90 |
| `backend/app/api/v1/routes_courses.py` | Production | Course catalog CRUD endpoints | ~140 |
| `backend/app/api/v1/routes_rooms.py` | Production | Classroom and laboratory CRUD endpoints | ~130 |
| `backend/app/api/v1/routes_preferences.py` | Production | Instructor preference submission/lookup endpoints | ~100 |
| `backend/tests/test_courses_api.py` | Test | Unit and validation tests for Courses | ~130 |
| `backend/tests/test_rooms_api.py` | Test | Boundary and filter tests for Rooms | ~110 |
| `backend/tests/test_preferences_api.py` | Test | Preference submission and query tests | ~100 |
| **Total LOC Expected** | | | **~800 LOC** (Compliant: > 400 LOC) |

---

## 5. Verification Commands

Run the following commands to verify implementation correctness:
```bash
# 1. Run all new REST API tests
pytest backend/tests/test_courses_api.py backend/tests/test_rooms_api.py backend/tests/test_preferences_api.py -v

# 2. Check test coverage
pytest --cov=app/api/v1 backend/tests/

# 3. Test interactively via Swagger UI
uvicorn app.main:app --reload --port 8000
# Open browser at: http://127.0.0.1:8000/api/v1/docs
```

---

## 6. Video Demonstration Coordination
Tony will present **Segment 2** (0:45 - 1:45) demonstrating the Swagger UI at `http://localhost:8000/api/v1/docs`: creating a course, triggering a 409 conflict, demonstrating capacity boundary validation (422), and querying filtered results.
