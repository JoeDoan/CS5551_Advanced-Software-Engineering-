# Faculty Commercialization Advisor: deployment brief for UM's ChatGPT environment

Status: draft for Prof. Lee and the technology office. Items marked **(assumption)** are not confirmed. Numbers are from the project's own tests (see `docs/plans/commercialization_advisor_v2_plan.md`, section 12), not from real faculty use.

## 1. What it is
An assistant that answers faculty process questions from quoted approved sources, explains commercialization terms in plain language, asks follow-up questions about readiness, and refers legal and IP judgment to staff. It never says whether something is patentable, novel or worth filing.

## 2. Content to load, with versions
| Source | Version |
| :--- | :--- |
| UM Collected Rules 100.020, Invention and Patent Regulations | Amended 6-24-21 |
| UM Collected Rules 100.030, Copyright Regulations | Amended 6-24-21 |
| UM Collected Rules 330.015, Conflict of Interest | Amended 9-12-24 |
| UM Collected Rules 420.030, Federal Grant Agencies | Amended 8-24-12 |
| UMKC Financial Conflict of Interest (FCOI) Policy | June 2026 |
| UMKC Office of Research and Innovation: Ownership, Intellectual Property | Web pages, retrieved 2026-11-01 |
| Plain-language glossary (14 terms) | Written by the project team; **draft, not yet reviewed** |

The 425 policy passages are verbatim extracts (`backend/data/policies/corpus.json`). Re-extract when a source changes. Process and timeline guidance is **not loaded**: no approved source has been named (open question 1).

## 3. System rules (enforced in code today; to be written as instructions in ChatGPT)
1. Answer a policy question only with a quoted passage, its source title, version and link. If nothing matches, say so and refer.
2. Glossary answers are labelled "draft, not yet reviewed" until the technology office fills in a reviewer and date.
3. Refer, never answer: patentability, novelty, inventorship, whether to file, publish, sign or consult, and how long a review will take. A referral names the Office of Technology Commercialization and lists what to bring.
4. Never state a verdict, however the question is phrased or pressured.
5. Ask for no confidential invention details. Work from what the author types.

## 4. Disabled or out of scope
Legal advice; any score or grade for an invention; inventor lists; review-time estimates; submission to the technology office; storage of drafts or papers; external prior-art or patent lookups.

## 5. Check on every content update
Re-run `backend/eval` and the advisor tests before publishing. Current results on our frozen tests:
- Boundary: 0 verdicts across the 30-question gold set, 25 synthetic scenarios and 749 rephrasing cases. This is a result on our tests, not a proof.
- Definitions: 6 of 6. False refusals: 0 of 30.
- **Policy retrieval: right passage in the top 5 for 14 of 18 questions** (target was 16). Four questions still miss. Faculty should see the quoted source and its link so a wrong match is visible.
- Readiness coach: flagged all 14 planted gaps; reported 2 of 11 clearly stated points as missing because it reads only the draft.

**Important:** ChatGPT cannot run our code. The rules in section 3 become prompt instructions there, which are weaker than the code checks above. The 749-case tests do not carry over. Re-run the same questions by hand in ChatGPT before launch **(assumption: this is the deployment route; the alternative is hosting our app)**.

## 6. Owner and cadence **(assumption)**
- Content owner: a named technology-office reviewer, who also signs off the glossary.
- Technical owner: the project team through the end of the course, then to be named.
- Review sources and glossary each semester and whenever UM Collected Rules or the FCOI policy change.

## 7. Open questions
1. Which guidance documents are approved sources for process and timeline answers?
2. Who reviews the glossary and question bank, and by when?
3. **What logging and retention terms apply in UM's ChatGPT environment?** Until this is answered, tell faculty not to paste unpublished invention details.
4. Can we run one real paper, with consent, against real faculty scenarios?
