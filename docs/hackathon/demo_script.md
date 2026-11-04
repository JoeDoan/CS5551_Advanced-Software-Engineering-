# Hack-a-thon Demo Script: "Predict, Simulate, Solve, Explain"

**Event:** Nov 8, 2026 | **Presenter:** Tony Nguyen | **Target length:** about 5:50 with the Commercialization part, 4:30 without it (cut list at the bottom if you get less)
**Language level:** short sentences, easy to say out loud. Every number below was checked in the running app.

**One-line pitch:** "OptiSched predicts next term's demand, finds the rooms that will break, and lets you ask what-if questions in plain English. A language model reads the question. A mathematical solver makes every scheduling decision."

---

## Before You Go On Stage (do this 30 minutes early)

1. **Rebuild-safe start.** In `backend/` (PowerShell). Your key is read from the git-ignored `backend/.env`.
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   $env:REBUILD_STALE_DB = "true"    # rebuilds an out-of-date database, keeps a .bak copy
   $env:DEMO_WARMUP = "true"         # solves the baseline + primes Claude in the background
   python -m uvicorn app.main:app --port 8000
   ```
2. **Frontend.** In `frontend/`:
   ```powershell
   npm run dev
   ```
3. **Check the console.** Wait for these lines (about 20 to 40 seconds):
   - `Application startup complete.`
   - `Warm-up: baseline timetable solved and cached.`
   - `Warm-up: Claude structured-output schema primed.` (only if the key is set)
   - If you see `DATABASE SCHEMA IS OUT OF DATE`, you forgot `REBUILD_STALE_DB`. Restart with it.
4. **Check health:** open `http://localhost:8000/api/v1/health`. It must say `"status": "healthy"`.
5. **Browser tabs (log in before the demo, all one-click):**
   - Tab 1: `http://localhost:5173/insights` signed in as **Course Coordinator**
   - Tab 2: a private window signed in as **Faculty Instructor** (Dr. Yugyung Lee), open on Insights
   - Tab 3: `http://localhost:5173/commercialization` signed in as **Course Coordinator**. Have `docs/samples/sample_paper_bridge_cracks.pdf` ready to drag in. Leave **Use Claude** unticked.
6. **Dry run once.** On Tab 1: What-If Simulator, tick the buyout box, pick Dr. Yugyung Lee, Run. Then Ask OptiSched, one prompt. This also warms the browser.
   Then on Tab 3: drop the sample PDF once, answer "Yes" to the course-release question, and press **Simulate course buyout impact** (the first solve took about 20 s in testing; the baseline is cached after). Reload the page afterwards so the demo starts clean.
7. **Do not restart the backend after step 6.** The baseline is cached in memory. A restart costs you 20 to 40 seconds of waiting on stage.
8. Plug in the laptop. Turn off notifications. Zoom the browser to 110%.

---

## Part 1: The Problem (0:00 - 0:30)
**On screen:** the Insights page, Demand Forecast tab.

> "Every semester, a department has to build a timetable.
> Room sizes, instructor loads, and preferences all fight each other.
> The hard part is not building one timetable. The hard part is asking, *what if*.
> What if enrollment grows? What if a professor wins a grant and teaches less?
>
> OptiSched answers that in four steps: **predict, simulate, solve, explain**.
> And one rule: the language model never makes a scheduling decision."

---

## Part 2: Predict Demand & Size Classrooms (0:30 - 1:10)
**On screen:** Demand Forecast & Holdout Benchmark tab (`uiuc_foia` 10-year real registrar profile or `umkc` department sandbox).

> "First, we predict next-term enrollment from 10 years of real UIUC FOIA registrar records: 22,991 raw catalog sections distilled into 800 course-semester records across 40 active STEM courses and 20 terms from Fall 2016 through Spring 2026.
> We train on the first 19 terms and hold out the final term, Spring 2026, to test our forecasts against actual enrollments.
>
> A point forecast alone under-predicts roughly half of courses. So we calibrate split conformal prediction intervals on 600 rolling-origin residuals to produce 80% and 95% upper demand bounds."

**Point at the benchmark table:**

> "On the held-out Spring 2026 term, Pooled Ridge reaches a point MAE of 17.24 seats versus 18.03 for Seasonal Naive and 28.25 for copying last term.
> Actual Spring 2026 enrollment falls inside our 95% conformal interval for 39 of 40 courses (97.5%) and inside our 80% interval for 34 of 40 courses (85.0%).
> Most importantly, sizing rooms to our 80% conformal upper bound cuts overflowed courses from 9 down to 2 and reduces unseated student seats by 84.6%, from 169 seats down to 26."

**Numbers (`uiuc_foia` 10-Year Real Registrar Holdout):** champion `pooled_ridge` (MAE 17.24 seats), `seasonal_naive` (MAE 18.03 seats), `copy_last_term` (MAE 28.25 seats), 95% PI coverage 97.5% (39/40), 80% PI coverage 85.0% (34/40), room overflows 9 -> 2, unseated seats 169 -> 26 (-84.6%). *(If switched to the `umkc` 6-semester synthetic sandbox profile: `damped_trend` MAE 3.25, 80% PI coverage 82.5%.)*

---

## Part 3: Find the Bottlenecks (1:10 - 1:55)
**On screen:** click **Bottlenecks**.

> "Now, which rooms will break?
> Look at the *capacity cliff* list.
> **BIOL 108, CHEM 432, and ECE 380** have only **7.1 percent** headroom.
> Grow any of them by 8 percent, and *no room fits them at all*."

**Point at the seat table:**

> "And look here. Two courses need 100 or more seats. We have exactly two rooms that big.
> This list is simple arithmetic, not machine learning. We label it that way."

**Numbers:** tiers: 0 critical, 1 high (CHEM 432), 2 watch, 37 OK. Seats needed 100+: 2 courses, 2 rooms. 60+: 11 courses, 4 rooms.

---

## Part 4: Simulate and Solve (1:55 - 2:50)
**On screen:** click **What-If Simulator**. Tick the buyout box. Instructor: **Dr. Yugyung Lee**. Coverage: **No replacement**. Click **Run simulation**.

> "Now, a professor wins a grant. She needs a course release.
> First, we say *nobody covers it*."

**Result:** INFEASIBLE with the reason.

> "The solver says no. And it explains why.
> We have 40 courses and 20 instructors who can each teach two. That is exactly 40.
> One release leaves 39 for 40 courses. It is arithmetic. There is no slack."

**Change coverage to "Adjunct replacement". Click Run.** While it solves (10 to 20 seconds):

> "The solver is checking every constraint and searching for the best timetable. It is not guessing."

**Result:** OPTIMAL, one course moved.

> "One course moves to an adjunct. Everything else stays put.
> That is the default: *minimal change*. A published timetable should not be shaken for no reason.
> If you want, you can ask it to re-optimize everything. Then it moves nine or ten courses to chase a slightly better score."

---

## Part 5: Ask in Plain English (2:50 - 4:00)
**On screen:** click **Ask OptiSched**. Check the badge: it should say **Claude on (claude-opus-5-5)**.

**Type (or click Interpret after typing):**
`CS grows 20% and ECE 10%, and Dr. Rao gets a course release covered by an adjunct`

> "Now the fun part. I type a normal sentence.
> It shows me what it *understood*, as chips. I can remove any chip.
> Nothing runs until I click."

**Chips shown:** CS enrollment +20%, ECE enrollment +10%, Dr. Praveen Rao: buyout to 1 course (an adjunct covers). Click **Run this scenario**.

**Result:** INFEASIBLE.

> "Infeasible. And look at the reason.
> ECE 380 would need 31 seats. Our biggest lab has 30.
> The copilot found the capacity cliff by itself. No one told it."

**Click the x on the ECE chip. Click Run this scenario.** While it solves:

> "Let me remove the ECE part and run again."

**Result:** OPTIMAL. Read the "What this means" box.

> "Now it works. Eight courses move. Average satisfaction goes from 97 to about 90 percent.
> Why? CS 101 grows to 132 students. It no longer fits the 120-seat room. It must take our biggest hall, and that pushes other classes.
> Notice this box. It says *written from the solver's own numbers, not by a language model*."

**Claude moment. Type:** `What if Lee takes a buyout and CS enrollment goes up by a fifth?` Click **Interpret**.

> "One more. 'A fifth.' 'Lee' with no title. Our rule-based parser cannot read this.
> Claude can. It understood: Dr. Yugyung Lee, and CS plus 20 percent.
> If the two parsers disagree, we show a badge. We never hide it.
> And if Claude is down, the rule-based parser takes over automatically."

**Say the safety line:**

> "Claude only fills a form. Every value is checked against our real instructors and rooms.
> If it returns 500 percent growth, we clamp it. If it makes up a name, we drop it.
> We also tested a prompt-injection sentence. It produced nothing, and our checks would clamp anything out of range."

**Numbers:** eval set 30 prompts (20 dev, 10 held out). Rule parser 30/30. Claude 30/30, used on every prompt. Claude first call after start is slow (about 10 s); warm-up handles it.

---

## Part 6: Faculty Commercialization Advisor (4:00 - 5:15)
**On screen:** Tab 3, **Commercialization**, step 1.

> "One more problem. Faculty write great papers, but turning one into a startup means a long invention form and a maze of conflict-of-interest rules.
> So we added an advisor. Same rule: the model may *propose*, but code and quoted policy decide."

**Drag in the sample PDF. Click Draft disclosure.**

> "This is a made-up paper, labelled as such. In a second we get a draft of the real UMKC invention form.
> Every proposed answer shows the exact sentence it came from. If a value cannot be found in the paper, it is dropped.
> Eight proposed, five to confirm, thirteen left blank. The blanks are things only the author knows. We do not guess."

**Point at the yellow flags:**

> "It spotted a public talk on June 12. UMKC's guidance says that can start a patent clock. We show the date and say *confirm it*.
> It also saw federal funding, which adds a reporting duty."

**Click step 2. Answer Yes to students and course release.**

> "Now five short questions, then a checklist. Every rule on this list is a *quote* from the University of Missouri or UMKC policy, with its source and version. Nothing is paraphrased."

**Click Simulate course buyout impact.**

> "And this connects to what we just built. A course release changes the schedule. The same solver checks it: one course moves to an adjunct, and it is proven optimal."

**Back to step 2 policy box. Type:** `Who owns an invention I make using university resources?` Click **Search policies**.

> "Ask a policy question and you get the passage, not an opinion. Ask something off topic, like pizza, and it refuses."

**Click step 3, then Run prior-art and grant lookup. Remove the "bridge" pill first.**

> "Step 3 suggests markets as *hypotheses to test*. The lookup sends only the broad terms on screen, which you can edit. Today it shows saved results, and says so. It is related work, never a verdict on novelty."

**Click step 4, Download package.**

> "Last, one zip: the draft form, the cited checklist, a market note, and a one-page summary. There is no portal to submit to, so it opens an email to the technology office."

**Numbers:** sample paper: 8 proposed, 5 to confirm, 13 blank; public event 2026-06-12, filing window to about 2027-06-12; buyout: 1 course moves (ECE 380 to an adjunct), proven optimal; policy corpus 425 quoted passages from 7 sources; lookup 23 saved results retrieved 2026-11-02.

---

## Part 7: Privacy for Faculty (5:15 - 5:30)
**On screen:** switch to **Tab 2** (Faculty, Dr. Yugyung Lee). Insights, What-If Simulator.

> "Faculty see a smaller tool. They can only simulate *their own* buyout.
> The server blocks anything else. And other professors appear as 'Colleague'.
> No one sees a coworker's satisfaction or priority."

---

## Part 8: Close and Honesty (5:30 - 5:50)
**On screen:** the **Limitations slide** (`limitations_slide.pptx`).

> "Here is what this is not.
> The enrollment data is synthetic. The dataset is small. We never save what-if runs.
> The commercialization draft is only tested on a made-up paper, and its wording needs review by the technology office before real use.
> To make it real, we need registrar data and a real validation.
>
> What we *do* have: a forecast with honest uncertainty, a solver that enforces every hard constraint and tells you when a result is provably optimal, and a language model that is not allowed to decide.
> Thank you."

---

## If Something Breaks

| Problem | What to do |
| :--- | :--- |
| Claude is slow or fails | The page shows "Claude was unavailable" and uses the rule-based parser. Keep going. Say: "That is the fallback working." |
| Solver is taking long | Talk through "proving optimal". Next time pick the **10 s** limit in the dropdown. |
| First click is slow | You skipped the warm-up. Say nothing, run the solver while you explain the arithmetic. |
| Page shows a red error | Check `http://localhost:8000/api/v1/health`. `degraded` means the database is out of date: restart with `REBUILD_STALE_DB=true`. |
| Login fails | Use the one-click demo buttons, not typed passwords. |
| Commercialization upload fails or hangs | Use "Or paste text instead" with the paper text. Same draft. |
| Lookup is slow or empty | It is saved results by default. If live mode was switched on and fails, it falls back and says so. |
| Buyout solve is slow on Tab 3 | You skipped the dry run. Read the policy citations while it solves. |
| Backend died | Restart (step 1). Skip to Part 5, it still works in rule-based mode. |
| No internet | Claude is skipped automatically. Say so, and show the rule-based result. |

## Cut List (if you have less time)

- 4:30: drop Part 6 (commercialization) entirely.
- 3:30: also drop Part 7 (faculty privacy) and the "re-optimize" sentence.
- 3:00: also drop the Claude "a fifth" moment and the bottleneck seat table.
- 2:00: Parts 1, 3, 5 only (problem, bottlenecks, one copilot run), then the limitations slide.
- Shorter commercialization (about 0:45): upload, point at one evidence quote and the yellow flags, show the cited checklist, download the zip. Skip policy box and lookup.

---

## Questions You Will Get (honest answers)

**Is the data real?** The 20 faculty, 40 courses and 12 rooms are modeled on the UMKC School of Science and Engineering. The enrollment history is synthetic and labelled as such. We tested the method, not real-world accuracy.

**How do you know the forecast works?** On the synthetic data, the best model beats the seasonal baseline (MAE 3.25 vs 3.79) and its intervals cover held-out points 82.5% of the time. Because we generated the data, that validates our pipeline. It does not prove real-world accuracy. With real data we would redo it.

**What stops the language model from making up a schedule?** It cannot. It only returns a small form: departments, percentages, instructor names. We validate every field against the database, clamp numbers, and show you the result before anything runs. The explanation text is built from the solver's numbers, not written by a model.

**Why not just ask an LLM to build the timetable?** An LLM cannot guarantee a timetable has no double-booked room. CP-SAT enforces that as a hard constraint, and when a scenario is impossible it tells you exactly why. It also reports whether the result is provably optimal or only the best found in the time limit.

**What happens when Claude is down?** The rule-based parser takes over and the page says so. In our 30-prompt test both parsers got 30 of 30, but the rule parser fails on phrasing like "a fifth" and warns you instead of guessing.

**How big can it get?** Today: 40 courses, 20 instructors, 12 rooms. Solves take about 10 to 20 seconds and are proven optimal. We have not tested a full university.

**Is faculty data private?** Faculty can only simulate their own buyout, and other instructors are shown as "Colleague".

**What did you not build?** Real registrar integration, a reviewer screen for the technology office, and patent search.

**Does the advisor decide if something is patentable or allowed?** No. It never gives a novelty or patentability verdict and never says a conflict is permitted. It shows quoted policy and tells the author what to ask the office.

**Where does the paper go?** It is read in memory and not saved. By default the text stays on our server. Only if you tick the Claude box is it sent to Anthropic's API, and the page says so. Zero data retention would be an account agreement, which we have not set up.

**Why not search patents?** We found no patent source we could verify without a key, so we do not claim one. Papers come from OpenAlex and grants from NIH RePORTER, as saved results by default and live only if switched on.

**Can it submit to the technology office?** There is no online portal. It builds a zip and opens an email.

---

## Numbers Cheat Sheet

| What | Value |
| :--- | :--- |
| Dataset | 20 faculty, 40 courses, 12 rooms, 6 semesters |
| Forecast target | Spring 2027 (semester 6), history Fall 2024 to Fall 2026 |
| Best model | damped trend: MAE 3.25, sMAPE 6.46% |
| Baseline | seasonal naive: MAE 3.79, sMAPE 7.83% |
| Interval check | 80% band covered 82.5% of held-out points |
| Capacity cliffs | BIOL 108, CHEM 432, ECE 380: +7.1%. BIOL 109, MATH 110: +15.4% |
| Instructor slack | 40 courses, 20 instructors x 2 = 40: zero slack |
| Buyout, minimal change | 1 course moves |
| Buyout, re-optimize | about 9 to 10 courses move |
| CS +20% and Rao adjunct | 8 courses move, satisfaction 97.0% to 90.5% |
| Copilot eval | 30 prompts, 30/30 rules, 30/30 Claude |
| Commercialization | policy corpus 425 passages, 26 form fields (9 extract, 7 extract and verify, 10 human only), 9 industries |
| Tests | re-run both suites before the event; the counts above were from before the commercialization work |

Numbers can shift slightly if the seed data or solver version changes. Re-run the dry run (step 6) before the event.
