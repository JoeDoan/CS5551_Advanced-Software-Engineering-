# OptiSched: Uncertainty-Aware Enrollment Forecasting with CP-SAT Course Scheduling

## Overview

OptiSched forecasts next-term enrollment for each course, attaches calibrated 80% and 95% prediction intervals, and sizes each room to the 80% upper bound. A Google OR-Tools CP-SAT model then assigns rooms, time slots and instructors with zero hard conflicts, using a 3-tier faculty preference hierarchy.

## Data and evaluation

- **Data.** Public UIUC registrar records (FOIA). 22,991 sections aggregated into 800 course-term enrollments, 40 STEM courses over 20 terms.
- **Training data.** 19 terms, Fall 2016 to Fall 2025. **Forecast target.** Next term.
- **Test term.** Spring 2026, held out, 40 courses, real enrollment.
- **Real inputs.** Enrollment history and instructors' 2-year teaching history. **Simulated inputs.** Room pool, preference weights, What-If scenarios.
- **Baselines.** Copy prior term (Fall 2025) and point forecast, each sized at +5%.

## Results on held-out Spring 2026

| Metric | Copy prior term | Point forecast | OptiSched 80% bound |
|:---|:---:|:---:|:---:|
| Forecast MAE (seats) | 28.25 | 17.24 | 17.24 |
| Overflowed courses | 8 / 40 | 9 / 40 | **2 / 40** |
| Unseated students | 338 | 153 | **60** |
| Hard conflicts | 0 | 0 | **0** |

- Unseated students fall 61% against the point forecast and 82% against copying the prior term.
- Interval coverage is 85% (34/40) at 80% and 97.5% (39/40) at 95%.
- Seat utilization is 64.9%, against 64.5% in the actual UIUC schedule.
- On the 25 courses with a teaching history, 84% (21/25) keep the instructor's usual days and slot.

**Who benefits.** Students face fewer first-week seat shortages in high-demand courses. Administrators make fewer room changes after registration, with no loss in seat utilization.

## Working demonstration

The What-If simulator re-solves a future term as a dry run for three scenarios: an enrollment surge (CS +20%, STAT +15%), an instructor unavailable (one-course grant release), and a room reassignment (all capacities × 0.9). It reports metric changes and every course that moved.

## Extension: Faculty Commercialization Advisor

Drafts a UM-16C invention disclosure (26 fields) from an uploaded paper, retrieves relevant clauses from 425 passages across 7 UM System and UMKC policy sources, and links to the instructor-release What-If scenario to check teaching coverage.
