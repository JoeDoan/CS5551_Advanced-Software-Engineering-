# Sprint 1 — 5-Minute Video Demonstration Script (Simple ESL English)

**Total Time Cap:** Strictly under **5:00 minutes** (Target: **4:40 – 4:50**)  
**Language Level:** Clear, natural, everyday academic English (short sentences, easy to pronounce).  
**Before Recording Checklist:**
1. Terminal 1 (`backend/`): run `uvicorn app.main:app --reload --port 8000`
2. Terminal 2 (`frontend/`): run `npm run dev`
3. Browser Tab 1: Open `http://localhost:5173` (React App on Dashboard)
4. Browser Tab 2: Open `http://localhost:8000/api/v1/docs` (FastAPI Swagger UI)
5. Browser Tab 3: Open your GitHub repository page (`https://github.com/JoeDoan/CS5551_Advanced-Software-Engineering-`)

---

## Segment 1: Introduction & System Architecture (0:00 – 0:45)
**Presenter:** Joe Doan (45 seconds)  
**On Screen:** Show the GitHub repository briefly, then switch to the React Dashboard at `http://localhost:5173`.

> **Spoken Script (Joe):**  
> "Hello Professor. We are the **UMKC Course Timetable Scheduler** team.  
> Our team members are Joe Doan, Tony Nguyen, Tina Nguyen, and Salvatore Nigro.  
>   
> The goal of our project is to automate university course scheduling using **Google OR-Tools CP-SAT**.  
> In Sprint 0, we built the prototype solver and project skeleton.  
> In **Sprint 1**, we turned our prototype into a full-stack web application.  
>   
> Our backend uses **FastAPI** and **SQLite** with automatic database seeding for 40 UMKC courses, 20 instructors, 12 rooms, and 6 semesters.  
> Our frontend uses **React**, **TypeScript**, and **FullCalendar**.  
> Every team member contributed over 750 lines of production and test code.  
> Now, Tony will demonstrate our backend APIs and solver service."

---

## Segment 2: Backend CRUD APIs, Seeder & Validation (0:45 – 1:45)
**Presenter:** Tony Nguyen (60 seconds)  
**On Screen:** Switch to Browser Tab 2 (`http://localhost:8000/api/v1/docs` — Swagger UI).

> **Spoken Script (Tony):**  
> "Thank you, Joe. I am Tony Nguyen, and I worked on the backend APIs, database seeder, and solver integration.  
>   
> First, when our server starts, our idempotent seeder automatically loads all UMKC campuses, buildings, rooms, courses, instructors, and time slots into SQLite.  
> *(Click `GET /api/v1/courses` -> Try it out -> Execute)*  
> Here in Swagger UI, calling `GET /api/v1/courses` returns our 40 seeded UMKC courses. We can also filter courses by department, such as `CS`.  
>   
> Next, let's test our input validation and error handling.  
> *(Click `POST /api/v1/courses` -> Try it out -> Send duplicate course code `"CS 101"`)*  
> If we try to create a course with an existing course code like `CS 101`, the API blocks it and returns **HTTP 409 Conflict**.  
> *(Scroll to `POST /api/v1/rooms` -> Try it out -> Enter `"capacity": -10` -> Execute)*  
> Similarly, if we submit a room with a negative capacity, Pydantic validation rejects it with **HTTP 422 Unprocessable Entity**.  
>   
> We also built `POST /api/v1/solver/run` to run the CP-SAT solver directly from the API and save the schedule into SQLite.  
> Now, Tina will show the instructor preferences portal."

---

## Segment 3: Interactive Instructor Preferences & Toast System (1:45 – 2:45)
**Presenter:** Tina Nguyen (60 seconds)  
**On Screen:** Switch to Browser Tab 1 (`http://localhost:5173/preferences` — React App).

> **Spoken Script (Tina):**  
> "Hi everyone, I am Tina Nguyen. In Sprint 1, I implemented the interactive **Instructor Preferences Portal**, the **Toast notification system**, the **Schedule Filters**, and the **CSV Export** feature.  
>   
> Here on the Preferences page, instructors can select their name from the dropdown.  
> The time slots below are loaded dynamically from our backend `/api/v1/time-slots` catalog.  
>   
> *(Click `Reset` button, then click `Save Preferences`)*  
> First, if I reset the form and click **Save Preferences** without selecting any day or time slot, our client-side validation blocks the submission and shows a red **error toast**.  
>   
> *(Click `Tuesday (T)` and `Thursday (R)`, then click `09:30 - 10:45` and `11:00 - 12:15`, then click `Save Preferences`)*  
> Now, when I select Tuesday and Thursday, pick two time slots, and click **Save Preferences**, the form sends a `POST` request to `/api/v1/preferences` and shows a green **success toast** confirming that the preferences are saved in the database.  
> Next, Sal will demonstrate the interactive schedule calendar and solver execution."

---

## Segment 4: FullCalendar Matrix, Multi-Filters, CSV Export & Live Solver (2:45 – 4:00)
**Presenter:** Salvatore Nigro (75 seconds)  
**On Screen:** Click **Schedule** in the left sidebar (`http://localhost:5173/schedule`), then **Admin** (`http://localhost:5173/admin`).

> **Spoken Script (Sal):**  
> "Hello, I am Salvatore Nigro. I built the reusable UI component library, the frontend API service layer, and the FullCalendar schedule integration.  
>   
> Here on the **Master Schedule Matrix** page, FullCalendar displays the weekly timetable loaded live from our SQLite backend across all 6 semesters.  
> Each department is color-coded: blue for Computer Science, purple for Math, and green for ECE.  
>   
> *(Select `CS (Computer Science)` in the Department filter, then type `Lee` or `204` in the search box, then click `Reset Filters`)*  
> Using the filter toolbar at the top, coordinators can filter the calendar in real time by department or search by course code, instructor name, or room number without reloading the page.  
>   
> *(Click `Export CSV` button at the top right)*  
> When we click **Export CSV**, the browser immediately downloads a structured CSV file of the current semester schedule for department review.  
>   
> *(Click `Admin` in the left sidebar -> Click `Execute Solver (Semester 1)` button)*  
> Finally, on the **Admin** page, clicking **Execute Solver** calls `POST /api/v1/solver/run`, solves all 40 courses to **OPTIMAL** in less than one second with zero conflicts, and displays the live satisfaction rate.  
> Now, Joe will wrap up with our automated test results."

---

## Segment 5: Automated Test Suites & Wrap-Up (4:00 – 5:00)
**Presenter:** Joe Doan (50 seconds)  
**On Screen:** Show Terminal 1 (`pytest tests/ -v`) and Terminal 2 (`npm test`).

> **Spoken Script (Joe):**  
> "To finish our demo, let's look at our automated test suites.  
>   
> *(Show Terminal 1 running `PYTHONPATH=. pytest tests/ -v`)*  
> On the backend, we have **43 Pytest unit and integration tests** plus **25 CP-SAT solver verification tests**. As you can see, all 43 Pytest tests pass 100%, covering CRUD operations, database seeding idempotency, preference rules, and solver persistence.  
>   
> *(Show Terminal 2 running `npm test` in `frontend/`)*  
> On the frontend, we have **20 Vitest test files with 68 automated tests**, and all 68 tests pass with a clean production build.  
>   
> In summary, our team completed all Sprint 1 goals with over 110 passing automated tests and full Git contribution compliance.  
> Thank you for watching!"
