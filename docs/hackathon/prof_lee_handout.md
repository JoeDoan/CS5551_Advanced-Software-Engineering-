# OptiSched: Uncertainty-Aware Academic Scheduling & Faculty Operations Platform

## Overview

OptiSched is a neuro-symbolic academic scheduling platform built for university departments. Its core engine combines **10-year enrollment time-series forecasting**, **split conformal prediction intervals**, and a **Google OR-Tools CP-SAT constraint solver** with a **3-tier faculty preference hierarchy**. On top of the core scheduler, we added a **Faculty Commercialization Advisor** that helps faculty draft UM-16C disclosures from research papers and simulate how a grant course buyout affects the department schedule.

## Core Pillar 1: 10-Year Enrollment Forecasting & CP-SAT Schedule Optimization

1. **10-Year Real UIUC FOIA Dataset.** Our deterministic ETL pipeline processes 10 academic years from Fall 2016 through Spring 2026, distilling 22,991 raw catalog sections into **800 course-semester records** across 40 active STEM courses and 20 terms. We train on the first 19 terms and hold out the final term, Spring 2026, to validate predictions against actual registrar enrollments.
2. **Pooled Ridge Forecasting + Split Conformal Prediction.** On the Spring 2026 holdout, Pooled Ridge achieves a point MAE of **17.24 seats** vs **18.03 seats** for Seasonal Naive and **28.25 seats** for prior-term copy. Because point forecasts alone under-predict roughly half of courses, we calibrate split conformal intervals on 600 rolling-origin residuals to produce **80% and 95% demand bounds** for risk-aware classroom sizing.
3. **3-Tier Preference-Aware CP-SAT Solver.** Enforces zero room, instructor, and time-slot overlaps while maximizing instructor preference satisfaction across three precedence tiers: **per-course overrides**, **general semester availability**, and **2-year causal teaching habits**, scored with integer weights across **40% Day, 40% Time Slot, and 20% Room/Layout**. When physical room or instructor limits make a request impossible, the solver proves infeasibility and diagnoses the exact bottleneck.
4. **Shift Evaluation From Symmetric MAE to Asymmetric Overflow Risk.** In university scheduling, assigning a room with 15 extra seats is free, whereas under-sizing a room by 15 seats causes first-week student overflows. Evaluating the pipeline by **unseated-student shortage** and **empirical interval coverage** captures the real operational value of conformal room sizing.

### Verified Holdout Validation Against Actual Spring 2026 Enrollments

- **Empirical conformal coverage.** On the 40 held-out Spring 2026 courses, actual registrar enrollment falls inside our 95% conformal interval for **39 of 40 courses, or 97.5%**, and inside our 80% conformal interval for **34 of 40 courses, or 85.0%**.
- **Classroom overflow and seat-shortage reduction.** Allocating rooms using point forecasts results in **9 overflowed courses and 169 unseated student seats**, and copying prior-term enrollment results in **8 overflowed courses and 199 unseated seats**. Sizing rooms with our **80% conformal upper bound** cuts actual Spring 2026 room overflows down to **2 of 40 courses** and reduces unseated student seats by **84.6%, from 169 down to 26 seats**, while maintaining **84.0% faculty habit continuity**.

## Add-On Pillar 2: Faculty Commercialization & Policy Retrieval Advisor

When faculty commercialize research, they often need both compliance guidance and a teaching release. Our 4-step add-on connects both workflows:

- **Step 1 & 2: Paper-to-UM-16C Drafter & Policy Retrieval.** Faculty drop in a research paper PDF in memory to draft the 26 fields of the UM-16C invention disclosure with verbatim supporting quotes, then answer targeted questions to build a compliance checklist backed by **BM25 keyword retrieval over 425 indexed passages across 7 UM System and UMKC policy documents**.
- **Step 3 & 4: Market Validation, Export & Live Course-Buyout Check.** Suggests testable NAICS and SBIR or STTR hypotheses, exports a zip package in memory, and triggers the live **CP-SAT Course-Release Simulator** to show which course moves and which colleague or adjunct covers it.
- **Honest Scope & Status.** Gives no patentability or legal opinion, performs no patent search, stores nothing on a server, and has been tested on one synthetic paper so far without technology transfer office review.

## Advisor Feedback

We prepared this one-page brief to keep you updated on what our team is building for Hack-A-Roo on November 8. We would welcome any thoughts, suggestions, or feedback by email whenever convenient for you.
