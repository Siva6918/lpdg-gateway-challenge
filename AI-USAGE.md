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

## Real AI Mistakes and Edge Cases Caught and Corrected

### 1. Constant Baseline std=0 Silent Anomaly Suppression
**Issue:**
When writing the baseline wrapper and synthetic tests, we identified an edge case: if a gateway has zero variance across the 28-day baseline window (e.g., constant metric values throughout the full period, so standard deviation $\sigma = 0$), calculating the 3-sigma threshold $(mean + 3 \times std)$ without guardrails either divides by zero or evaluates conditions where an extreme surge could score zero flags if standard deviation is zero and condition requires $> mean + 3 \times std$. 

**How it was caught and tested:**
Identified during edge case analysis and formalised in an end-to-end regression test: `tests/test_e2e.py::TestRegressionStdZeroSilentFailure::test_constant_baseline_with_extreme_spike_scores_zero` and `test_nonzero_baseline_variance_with_spike_is_flagged`. This documents mathematically why gateways with completely stationary histories require variance to trigger 3-sigma detection.

### 2. Timezone-Aware Timestamp Handling
**Issue:**
In initial draft of `ranking_service.py`, `week_start` was converted via `str(week_start)` before passing to `pd.Timestamp()`. Without explicit UTC timezone assignment matching the Parquet dataset's UTC timestamps, pandas raised `TypeError: Cannot compare tz-naive and tz-aware` at runtime during comparison.

**Fix applied:**
Always normalize dates with `pd.Timestamp(week_date, tz="UTC")` throughout `ranking_service.py`. Fully covered in `tests/test_service.py` and `tests/test_api.py`.

---

*Last updated: 2026-09-11*
