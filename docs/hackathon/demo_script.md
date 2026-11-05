# Hack-A-Roo 3-Minute Demonstration Video & Live Pitch Script: "Predict, Buffer, Solve, Simulate"

**Submission Deadline:** November 9, 2026 (3-Minute Video + Poster + GitHub Repo)
**Final Live Demo:** November 13, 2026
**Team:** Joe Doan, Tony Nguyen, Tina Nguyen, Salvatore Nigro | **Faculty Advisor:** Prof. Yugyung Lee
**Target Length:** **3:00** (strictly timed for the Hack-A-Roo 3-minute demonstration video; every number below is verified in the running app)

---

## Pre-Recording / Pre-Stage Checklist (5 Minutes Before Recording)

1. **Start Backend (`backend/`):**
   ```bash
   cd backend
   python3 -m uvicorn app.main:app --port 8000
   ```
2. **Start Frontend (`frontend/`):**
   ```bash
   cd frontend
   npm run dev
   ```
3. **Verify Health & Active Dataset Profile (`uiuc_foia`):**
   - Open `http://localhost:8000/api/v1/health` (`"status": "healthy"`).
   - Open `http://localhost:5173/insights` signed in as **Course Coordinator**. Confirm the green badge says **`UIUC FOIA Registrar (2016–2025)`**.
4. **Pre-Open 3 Browser Tabs at 110% Zoom:**
   - **Tab 1 (`http://localhost:5173/insights`):** Demand Forecast & Held-Out Spring 2026 Benchmark (with the visual **Unseated Students Comparison Chart: 199 -> 169 -> 26**).
   - **Tab 2 (`http://localhost:5173/schedules`):** Master Schedule Matrix & 3-Tier Faculty Preferences.
   - **Tab 3 (`http://localhost:5173/commercialization`):** Faculty Commercialization Advisor (extension feature).

---

## 0:00 – 0:35 | 1. Innovation & How OptiSched Differs From Existing Systems
**On screen:** Tab 1 (`Insights -> Demand Forecast`), showing the 19-term historical curve, next-term forecast point, and blue 80% / 95% conformal bands.

> "Existing university scheduling tools treat next-semester enrollment as a single fixed number, usually copied from last semester.
> Because a single point estimate under-predicts roughly half of all classes, departments suffer first-week classroom overflows, locked-out students, and emergency room swaps.
>
> **OptiSched** fixes this by combining **uncertainty-aware enrollment forecasting** with a **Google OR-Tools CP-SAT constraint solver**.
> Importantly, we do not try to predict 10 years into the future. Instead, our Pooled Ridge model learns from **10 years of historical registrar data**—19 prior semesters—to forecast the **very next semester**, and calibrates **Split Conformal Prediction intervals** so the solver sizes rooms to an **80% upper demand bound**."

---

## 0:35 – 1:15 | 2. Visual Key Results & Evaluation Scope (Real Data vs. Simulated Scenarios)
**On screen:** Scroll slightly down on Tab 1 to the **Spring 2026 Held-Out Empirical Benchmark** card and point at the **Unseated Student Seats Visual Comparison Chart** and the **Evaluation Scope** callout.

> "Look at our held-out Spring 2026 validation across 40 active STEM courses:
> - Actual registrar enrollment lands inside our 95% conformal band for **39 of 40 courses (97.5%)** and inside our 80% band for **34 of 40 courses (85.0%)**, with a point MAE of **17.24 seats**.
> - More importantly, look at the visual comparison chart for unseated students:
>   - Sizing rooms by copying last term leaves **8 overflowed courses and 199 unseated students**.
>   - Sizing rooms by raw point forecasts still leaves **9 overflowed courses and 169 unseated students**.
>   - Sizing rooms with OptiSched's **80% conformal upper bound** cuts overflows down to **2 courses** and reduces unseated students by **84.6%, from 169 down to just 26 seats**—protecting students from Week-1 lockouts and saving administrators from emergency section splits.
>
> To be completely transparent about our evaluation: the **800 course-semester enrollments** from Fall 2016 through Spring 2026 come from **real UIUC FOIA registrar records**, while our classroom assignments, 3-tier faculty preferences, and counterfactual shocks run in a **controlled CP-SAT simulation environment**."

---

## 1:15 – 2:35 | 3. Complete Workflow & Live What-If Counterfactuals
**On screen:** Briefly flash Tab 2 (`Master Schedule`, 10 seconds) showing **0 hard conflicts** and **84.0% two-year faculty habit continuity**, then switch to Tab 1 -> **What-If Simulator** (`1-Click Demo Presets`) and **Ask OptiSched**.

> "From those demand bounds, our CP-SAT solver builds a conflict-free timetable across rooms, time slots, and our 3-tier faculty preference hierarchy—per-course overrides, general availability, and 2-year teaching habits—achieving **84% habit continuity and zero hard conflicts**.
>
> Now let's test how the schedule responds to three real operational shocks:
> 1. **Shock 1 — Enrollment Increases:** I click the **Enrollment Surge** preset (`CS +20%, STAT +15%`) with forecast sizing enabled. CP-SAT re-solves in seconds, shifting surging sections into larger lecture halls while keeping the rest of the timetable stable.
> 2. **Shock 2 — Instructor Unavailable:** Suppose a professor takes a one-course grant release. If we select **No replacement**, the solver mathematically proves the problem is **INFEASIBLE** because 20 faculty teaching at most 2 courses cannot cover 40 sections with one release. When we switch to **Colleague overload** or **Adjunct replacement**, the solver finds an **OPTIMAL** schedule that moves just **1 course**.
> 3. **Shock 3 — Classroom Reassigned:** In **Ask OptiSched**, we can also type in plain English or click **Classroom Reassigned (`0.9x` room capacity)**. The language model only parses the intent into chips—every scheduling decision is made by the mathematical CP-SAT solver."

---

## 2:35 – 3:00 | 4. Extension Feature: Faculty Commercialization Advisor & Closing
**On screen:** Tab 3 (`Commercialization Advisor`, 20 seconds).

> "Finally, as an optional extension for faculty who win research grants, our **Commercialization Advisor** drafts a 26-field **UM-16C** disclosure from a paper PDF, retrieves verbatim rules from **425 passages across 7 UM System and UMKC policy documents** via BM25, and links directly into the **Course-Release Simulator** we just saw.
>
> By uniting 10-year historical demand forecasting, split conformal risk bounds, and CP-SAT optimization, **OptiSched** cuts unseated student shortages by **84.6%** and turns academic scheduling from fragile guesswork into a mathematical guarantee. Thank you!"
