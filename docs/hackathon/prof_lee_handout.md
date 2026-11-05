# OptiSched: Uncertainty-Aware Academic Scheduling & Faculty Operations Platform

## Overview & Core Innovation

OptiSched integrates **uncertainty-aware next-semester enrollment forecasting** (**Pooled Ridge Regression** + **Split Conformal Prediction**) directly into a **Google OR-Tools CP-SAT constraint solver** with a **3-tier faculty preference hierarchy**. Unlike existing university scheduling systems that copy prior-term room assignments or size rooms to raw point forecasts, OptiSched sizes classrooms to calibrated **80% conformal upper bounds** so upside demand variance is absorbed before classes begin.

## Core Pillar 1: Next-Term Enrollment Forecasting (Trained on 10-Yr History) & CP-SAT Optimization

1. **Next-Term Forecasting Trained on 10 Years of Real UIUC FOIA Registrar Data.** Our deterministic ETL pipeline processes 10 academic years (`Fall 2016` through `Spring 2026`), distilling `22,991` raw catalog sections into **800 course-semester headcounts** across `40` active STEM courses and `20` terms. The model trains on **10 years of historical data (`19` prior terms) to forecast the single upcoming semester (`Spring 2026` held out)**—not a 10-year future projection.
2. **Pooled Ridge Forecasting + Split Conformal Prediction.** On the held-out Spring 2026 semester, Pooled Ridge achieves a point MAE of **17.24 seats** vs **18.03 seats** for Seasonal Naive and **28.25 seats** for copying prior-term enrollment (`39.0%` error reduction). Calibrating split conformal intervals on `600` rolling-origin residuals achieves **85.0% (`34/40`)** empirical coverage at the 80% bound and **97.5% (`39/40`)** coverage at the 95% bound.
3. **3-Tier Preference-Aware CP-SAT Solver & Counterfactual What-If Simulator.** Enforces zero room, instructor, and time-slot overlaps while maximizing instructor preferences across three precedence tiers (**per-course overrides**, **general semester availability**, and **2-year causal teaching habits**) scored across **40% Day, 40% Time Slot, and 20% Room/Layout**. Department coordinators can also simulate three live operational shocks in seconds: **enrollment surges**, **instructor unavailability (grant buyout)**, and **classroom reassignments**.
4. **Evaluation Scope Clarification (Real Data vs. Simulated Scenarios).** Enrollment trajectories (`800` course-terms), held-out Spring 2026 actuals, and 2-year modal teaching habits are **100% real UIUC FOIA registrar data**. The standardized 12-room / 6-slot constraint pool, 3-tier preference weights, and counterfactual What-If shocks are **simulated scheduling scenarios**.

### Verified Holdout Results & Practical Impact (Held-Out Spring 2026, 40 Courses)

- **84.6% Reduction in Unseated Students (`169 → 26 seats`):** Sizing rooms with raw point forecasts results in **9 overflowed courses and 169 unseated student seats**, and copying prior-term enrollment results in **8 overflowed courses and 199 unseated seats**. Sizing rooms with OptiSched's **80% conformal upper bound** cuts Spring 2026 room overflows down to **2 of 40 courses (`-77.8%`)** and reduces unseated student seats to **26 (`-84.6%`)** with **0 hard conflicts (`OPTIMAL`)** and **84.0% (`21/25`)** 2-year faculty habit continuity.
- **Benefits for Students & University Administrators:** Protects **students** from Week-1 classroom lockouts and delayed graduation bottlenecks in required STEM sequences, and saves **administrators** from emergency first-week section splits and room swaps.

## Extension Feature: Faculty Commercialization & Policy Retrieval Advisor

As an extension module connected to the course-release simulator, OptiSched helps faculty draft 26-field **UM-16C** invention disclosures from research paper PDFs in memory, retrieves compliance passages via **BM25 keyword search over 425 passages across 7 UM System and UMKC policy documents**, and invokes the **CP-SAT Course-Release Simulator** to verify whether the department timetable can absorb a grant teaching buyout.
