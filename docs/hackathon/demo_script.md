# OptiSched 3-Minute Demo Script

**Submission:** November 9, 2026 (video, poster, repository)
**Live demo:** November 13, 2026
**Team:** Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro. **Advisor:** Prof. Yugyung Lee.
**Length:** 3:00. Numbers below come from the running app on the `uiuc_foia` profile.

---

## Setup (5 minutes before recording)

1. Start the backend.
   ```bash
   cd backend
   python3 -m uvicorn app.main:app --port 8000
   ```
2. Start the frontend.
   ```bash
   cd frontend
   npm run dev
   ```
3. Sign in at `http://localhost:5173/login` as **Course Coordinator**. Confirm the badge reads `UIUC FOIA Registrar (2016–2025)`.
4. Open three tabs at 110% zoom.
   - `http://localhost:5173/insights` (Demand Forecast and the Spring 2026 benchmark).
   - `http://localhost:5173/schedule` (Master Schedule).
   - `http://localhost:5173/commercialization` (extension).

---

## 0:00 to 0:35 | Problem and approach
**On screen:** Insights, Demand Forecast. History line, next-term point, 80% and 95% bands.

> "Rooms are assigned before registration opens.
> If a room is sized to last term's headcount, or to a single forecast, students go without seats whenever demand runs high.
>
> OptiSched forecasts next-term enrollment for each course and attaches calibrated prediction intervals.
> It trains on 19 terms of real registrar data, Fall 2016 to Fall 2025.
> Each room is sized to the 80% upper bound, and a CP-SAT model assigns rooms, time slots and instructors."

---

## 0:35 to 1:15 | Results on a held-out term
**On screen:** Scroll to the Spring 2026 benchmark. Point at the unseated-seats chart and the Data and Evaluation box.

> "We held out Spring 2026, 40 courses, and compared against what actually happened.
> Forecast error is 17.24 seats, against 28.25 for copying last term.
> The 80% interval covered 34 of 40 courses. The 95% interval covered 39 of 40.
>
> Now unseated students, meaning enrollment above the assigned room's capacity.
> Copying last term leaves 338 students without a seat.
> Sizing to the point forecast leaves 153.
> Sizing to OptiSched's 80% bound leaves 60. That is 61% fewer than the point forecast, with seat utilization about the same as the real UIUC schedule.
>
> Enrollment and teaching history are real UIUC records. The room pool, preference weights and What-If scenarios are simulated."

---

## 1:15 to 2:35 | Full workflow and three What-If scenarios
**On screen:** Master Schedule for 10 seconds (0 hard conflicts). Then Insights, What-If Simulator, Quick Demo Scenarios.

> "From those room sizes, CP-SAT builds a timetable with zero hard conflicts.
> On courses with a teaching history, 84% keep the instructor's usual days and slot.
>
> Now three changes a department actually faces.
> 1. Enrollment surge. CS up 20%, STAT up 15%. The solver moves over-capacity sections to larger rooms.
> 2. Instructor unavailable. One professor takes a one-course grant release. With colleague coverage, one course moves and both solves are optimal.
> 3. Room reassigned. Every room loses 10% capacity. Courses above the new capacity move to rooms that fit.
>
> Each run is a dry run. Nothing is saved, and placements the scenario does not force to change stay where they are."

---

## 2:35 to 3:00 | Extension and close
**On screen:** Commercialization tab for 20 seconds.

> "One extension. For faculty commercializing research, OptiSched drafts a UM-16C disclosure from a paper, retrieves relevant clauses from 425 policy passages, and links to the instructor-release scenario you just saw.
>
> OptiSched connects calibrated demand forecasts to the scheduler, so rooms are sized for the demand that is likely, not just the average. Thank you."
