# Advisor v2: comparison of the two implementations

Date: 2026-11-07. Purpose: give the team the facts to decide which implementation goes forward. This is not a recommendation to merge either one.

## What was compared
| | `origin/main` | `feature/commercialization-advisor-coach` |
| :--- | :--- | :--- |
| Commit tested | `5d579ed` (PR #4 plus `f37ff65`) | `256ff54` (includes WP6, WP7 and the FOIA test fix) |
| Author | teammate `ddoan15nov-rgb` | Tony |
| Pushed | yes | no (a copy ending before WP6 is on `feature/commercialization-advisor-v2-wp1-5-tony`) |

Both implement the same plan: scope gate, glossary, readiness coach, verifier, advisor routes, UI, eval set and a deployment brief. They share history only up to `92d3159`, and 12 backend, eval, frontend and docs files were created on both sides. A merge gives 16 conflicts, so one side has to be chosen file by file.

## Results
Tests were run in a separate checkout of `origin/main`, with the project's own virtualenv.

| Check | `origin/main` | This branch |
| :--- | :--- | :--- |
| Backend tests | 255 passed, 1 failed | 1360 passed |
| Frontend tests | 160 passed | not re-run here |
| Frontend build | fails, 462 test-typing errors | same 462 errors (shared setup issue) |
| Policy retrieval on the branch's gold set (18 questions): Hit@5 | 12/18 | 14/18 |
| Same, Hit@1 and MRR | 8/18, 0.511 | not re-measured here (14/18 Hit@5 was recorded when the topic boost landed) |
| Policy retrieval on `origin/main`'s gold set (18 questions): Hit@5 | 18/18 | 18/18 |
| Boundary and concept items, branch gold set (12) | 12 correct | 12 correct |
| Non-policy items, `origin/main` gold set (12) | 12 correct | 8 correct |

The one failing backend test on `origin/main` is `test_uiuc_foia_zero_gpa_columns_and_offline_determinism`. It fails on Windows because of CRLF line endings and because the schedule files depend on the OR-Tools version. The fix is in `256ff54` and can be applied to `origin/main` on its own.

## How to read this
- **Neither gold set is independent.** Each was written by the team that built the matching system, and `origin/main` reports 18/18 and 25/25 on its own sets. Cross-running them is fairer, but is still not a held-out test.
- **Retrieval:** the branch scored higher on its own set and equalled `origin/main` on theirs. This suggests the branch retrieves at least as well, not that it is better.
- **Four items on `origin/main`'s set go wrong on this branch:**
  - `gold-28` (sponsor contract, "automatic exclusive licence") expects a referral, and this branch answers with policy quotes. This is a gap in the scope gate.
  - `gold-22` (what counts as a public disclosure) expects a concept explanation, and this branch answers with policy quotes.
  - `gold-21` (inventorship versus authorship) expects a concept explanation, and this branch refers it.
  - `gold-30` (parking permit fee) expects "out of scope", and this branch labels it "policy" with a no-match answer.
  The last two are probably labelling differences.
- **Only on this branch:** 749 rephrasing tests, a 0 to 2 scoring rubric with hard boundary gates, hash-frozen eval files with saved results, and a timeline referral that refuses to guess a review time.
- **Not compared:** the user interface, the readiness coach's quality, and response wording. The tests above do not cover them.

## Decision options
1. Take `origin/main` as the base and port selected parts of this branch: the rephrasing tests, the rubric, the timeline referral, the FOIA test fix.
2. Take this branch as the base and port what `origin/main` does better, starting with `gold-22` and `gold-28`.
3. Keep both for the report, and demo one.

## Reproduce
```bash
git worktree add --detach <folder> origin/main
cd <folder>/backend
PYTHONPATH=. <venv>/python -m pytest tests -q
PYTHONPATH=. <venv>/python eval/run_eval.py
```
The cross-run scripts compared the two gold sets, one running each set against the other side's search and advisor. They were scratch files and are not committed.
