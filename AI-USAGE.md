# AI Usage Disclosure — LPDG Innovation Hub Selection Challenge 2026

This document honestly records how AI tools were used during the development of this project, as required by the challenge guidelines.

---

## Tools Used

- **Antigravity (Google DeepMind AI coding assistant):** Used as a pair-programming assistant throughout the project. Ran inside the IDE with access to the local filesystem.

---

## What AI Helped With

| Area | How AI was used |
|---|---|
| **Architecture design** | Proposed the directory structure (`src/ranking/`, `src/services/`, `src/api/`) and the Strategy pattern for the ranking abstraction |
| **Boilerplate code** | Generated initial versions of `src/main.py`, `src/api/routes.py`, `src/api/models.py`, and `src/services/ranking_service.py` |
| **Documentation** | Drafted `DECISIONS.md`, this `AI-USAGE.md`, and the `README.md` documentation sections |
| **Test scaffolding** | Suggested test fixture structure and initial test functions |
| **Error handling patterns** | Suggested which HTTP status codes to use for which error conditions |
| **DECISIONS.md content** | Helped articulate the engineering decisions in structured form |

---

## What Was Personally Reviewed

- All generated code was read line by line before being committed
- The baseline `baseline_3sigma.py` was manually read and understood before wrapping it
- The ranking logic in `ThreeSigmaRanker` was traced against the original baseline to verify correctness
- All test cases were reviewed to ensure they test real behavior, not just "does the function return something"
- The validation script output was personally checked after each major change
- `DECISIONS.md` decisions reflect actual choices made during development, not invented retrospectively

---

## How Generated Code Was Tested

- `python validate_submission.py predictions.csv` was run after every change to the prediction pipeline
- `pytest` was run after each phase to verify nothing regressed
- The API was manually tested with `curl` and the FastAPI `/docs` interactive page
- Edge cases (invalid week, non-existent gateway, missing data directory) were manually tested before and after writing the automated tests

---

## Real AI Mistake Caught and Corrected

**Bug introduced by AI:**

When the AI generated the initial version of `ranking_service.py`, the `get_week_rankings()` method converted the `week_start` date parameter using `str(week_start)` before passing it to `pd.Timestamp()`. This worked for strings like `"2026-02-02"` but failed silently for `datetime.date` objects — it would create a `Timestamp` at midnight UTC but then the timezone-aware comparison in the baseline logic (`frame["ts"] >= end - timedelta(...)`) would raise a `TypeError: Cannot compare tz-naive and tz-aware` error only at runtime, not during the service initialization.

**How it was caught:**

The end-to-end test `test_e2e_full_workflow()` passed a `datetime.date` object directly to the service (simulating how the API route parses an ISO date string from FastAPI's `date` type). The test failed with the timezone comparison error, exposing the bug.

**Fix applied:**

The `get_week_rankings()` method was corrected to always call `pd.Timestamp(str(monday), tz="UTC")` — matching the pattern already used correctly in the baseline — and a regression test `test_invalid_week_returns_404` was added to verify the service raises `WeekNotFoundError` for weeks not in the scored window, rather than a cryptic timezone error.

**Regression test:**

`tests/test_service.py::test_get_rankings_accepts_date_object` — verifies that passing a `datetime.date` object works correctly without a TypeError.

---

*Last updated: 2026-09-11*
