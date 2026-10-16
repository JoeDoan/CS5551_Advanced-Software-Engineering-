# Sprint 1 — 5-Minute Video Demonstration Script (Single Presenter: Joe Doan)

**Presenter:** Joe Doan (presenting on behalf of the entire team: Joe Doan, Tony Nguyen, Tina Nguyen, and Salvatore Nigro)  
**Recorded Video (Panopto):** https://umsystem.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=835d036a-c31b-42cc-8b4a-b4e50145fcb9  
**Total Time Cap:** Strictly under **5:00 minutes** (Target: **4:30 – 4:45**)  
**Language Level:** Clear, simple ESL graduate-student English (short sentences, easy to read aloud smoothly).

---

## Pre-Recording Setup (Open These Before Hitting Record)

1. **Terminal 1 (`backend/`):**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
2. **Terminal 2 (`frontend/`):**
   ```bash
   cd frontend
   npm run dev
   ```
3. **Terminal 3 (Ready for Part 5 test run):**
   - Split into two tabs or keep two terminal windows ready: one in `backend/` and one in `frontend/`.
4. **Browser Tabs:**
   - **Tab 1:** `http://localhost:5173` (React App — start on the **Dashboard** page)
   - **Tab 2:** `http://localhost:8000/api/v1/docs` (FastAPI **Swagger UI**)
   - **Tab 3:** `https://github.com/JoeDoan/CS5551_Advanced-Software-Engineering-` (GitHub Repository)

---

## Part 1: Introduction & Project Overview (0:00 – 0:45)
**On Screen:** Start on **Tab 3 (GitHub repo)** for 15 seconds, then switch to **Tab 1 (React Dashboard `http://localhost:5173`)**.

> **Spoken Script (Joe):**  
> "Hello Professor. My name is Joe Doan.  
> Today I am presenting the Sprint 1 demonstration for our group.  
> Our team members are **Joe Doan**, **Tony Nguyen**, **Tina Nguyen**, and **Salvatore Nigro**.  
>   
> Out of the two project options for this course, our team chose the **Course Timetable Scheduler** project.  
> In Sprint 0, we set up our repository and migrated our **Google OR-Tools CP-SAT** solver prototype.  
> In **Sprint 1**, we turned that prototype into a working full-stack web application.  
>   
> Our backend uses **FastAPI** and **SQLite**, and our frontend uses **React**, **TypeScript**, and **FullCalendar**.  
> All four team members contributed more than 750 lines of production and test code on GitHub."

---

## Part 2: Backend CRUD APIs, Database Seeder & Validation (0:45 – 1:50)
**On Screen:** Switch to **Tab 2 (`http://localhost:8000/api/v1/docs` — FastAPI Swagger UI)**.

> **Spoken Script (Joe):**  
> "First, let's look at our backend REST APIs in Swagger UI, which were implemented by **Tony** and **me**.  
>   
> When the backend server starts, our database seeder automatically loads the UMKC dataset into SQLite.  
> This includes 2 campuses, 5 buildings, 12 rooms, 20 instructors, 40 courses, 14 time slots, and 6 semesters.  
>   
> *(Click `GET /api/v1/courses` -> Click `Try it out` -> Enter `CS` in `department` -> Click `Execute`)*  
> Here, when I call `GET /api/v1/courses` and filter by the `CS` department, the API returns our Computer Science courses from SQLite.  
>   
> Next, let's test our input validation and error handling.  
> *(Open `POST /api/v1/courses` -> Click `Try it out` -> Set `"course_code": "CS 101"` -> Click `Execute`)*  
> If I try to create a course with a duplicate code like `CS 101`, the server blocks it and returns **HTTP 409 Conflict**.  
>   
> *(Scroll down to `POST /api/v1/rooms` -> Click `Try it out` -> Set `"capacity": -10` -> Click `Execute`)*  
> And if I try to create a classroom with a negative capacity, Pydantic validation rejects the request with **HTTP 422 Unprocessable Entity**.  
>   
> We also have `POST /api/v1/admin/seed` and `POST /api/v1/solver/run` to seed the database and run the CP-SAT solver via REST API."

---

## Part 3: Instructor Preferences Portal & Toast Notifications (1:50 – 2:45)
**On Screen:** Switch to **Tab 1 (React App)** and click **Preferences** in the left sidebar (`http://localhost:5173/preferences`).

> **Spoken Script (Joe):**  
> "Now let's switch to the React frontend.  
> **Sal** built our reusable UI component library and API service layer, and **Tina** built the interactive **Preferences page**, **Toast notifications**, **Schedule Filters**, and **CSV Export**.  
>   
> Here on the **Instructor Preferences** page, an instructor can select their name from the dropdown.  
> The time slots below are loaded from our backend `/api/v1/time-slots` endpoint.  
>   
> *(Click `Reset`, then click `Save Preferences`)*  
> First, if I reset the form and click **Save Preferences** without choosing any day or time slot, our form validation blocks the request and shows a red **error toast** at the bottom right.  
>   
> *(Click `Tuesday (T)` and `Thursday (R)`, click `09:30 - 10:45` and `11:00 - 12:15`, then click `Save Preferences`)*  
> Now, when I select Tuesday and Thursday, pick two time slots, and click **Save Preferences**, the frontend sends a `POST` request to `/api/v1/preferences` and shows a green **success toast** confirming the data is saved in SQLite."

---

## Part 4: Schedule Calendar, Multi-Filters, CSV Export & Live Solver Run (2:45 – 3:55)
**On Screen:** Click **Schedule** in the left sidebar (`http://localhost:5173/schedule`), then click **Admin** (`http://localhost:5173/admin`).

> **Spoken Script (Joe):**  
> "Next, let's open the **Schedule** page.  
> Here, FullCalendar displays the weekly timetable loaded directly from our SQLite database across all 6 semesters.  
> Courses are color-coded by department: blue for Computer Science, purple for Math, and green for ECE.  
>   
> *(In the filter bar, select `CS (Computer Science)` from the Department dropdown, then type `204` or `Lee` in the search box, then click `Reset Filters`)*  
> Using the filter toolbar, we can filter the calendar in real time by department, or search by course code, instructor name, or room number without reloading the page.  
>   
> *(Click the `Export CSV` button at the top right)*  
> We can also click **Export CSV** at the top right to download the current semester schedule as a CSV file in one click.  
>   
> *(Click `Admin` in the left sidebar -> Click `Execute Solver (Semester 1)` button)*  
> Finally, on the **Admin** page, when I click **Execute Solver**, the frontend calls `POST /api/v1/solver/run`.  
> The backend runs Google OR-Tools CP-SAT, schedules all 40 courses to **OPTIMAL** in under one second with zero hard-constraint conflicts, saves the new schedule into SQLite, and shows the faculty satisfaction rate."

---

## Part 5: Automated Test Suites & Wrap-Up (3:55 – 4:45)
**On Screen:** Switch to **Terminal** to show backend Pytest (`pytest tests/ -v`) and frontend Vitest (`npm test`).

> **Spoken Script (Joe):**  
> "To conclude our demo, let's run our automated test suites in the terminal.  
>   
> *(In the `backend/` terminal, run `PYTHONPATH=. pytest tests/ -v`)*  
> On the backend, we have **43 Pytest unit and integration tests**, plus **25 solver verification tests**.  
> As shown here, all 43 Pytest tests pass 100%. They test our Course and Room CRUD APIs, database seeder idempotency, preference slot rules, and solver persistence.  
>   
> *(In the `frontend/` terminal, run `npm test`)*  
> On the frontend, we have **20 Vitest test files with 68 unit tests**, and all 68 tests pass with zero build errors.  
>   
> That completes our Sprint 1 demonstration. Thank you for watching, Professor!"
