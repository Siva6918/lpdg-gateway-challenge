# AI Usage Disclosure — LPDG Innovation Hub Selection Challenge 2026

This document honestly records how AI tools were used during the development of this project, as required by the challenge guidelines.

---

## Tools Used

The following AI tools were used during the development of the project:

* **Antigravity (Google DeepMind AI coding assistant):** Used as a pair-programming assistant within the IDE for implementation, debugging, project structure, and local development.
* **ChatGPT (OpenAI):** Used for understanding requirements, discussing architecture and implementation approaches, debugging errors, reviewing code and tests, and explaining technical concepts.
* **Claude (Anthropic):** Used for code review, reasoning about implementation details, identifying edge cases, and improving documentation and engineering decisions.

These tools were used as development assistants. Their suggestions and generated code were reviewed, adapted, and tested against the actual project requirements.

---

## What AI Helped With

| Area                      | How AI was used                                                                                                                                                                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Architecture design**   | Antigravity, ChatGPT, and Claude were used to discuss and evaluate the directory structure (`src/ranking/`, `src/services/`, `src/api/`) and the Strategy pattern used for the ranking abstraction. |
| **Boilerplate code**      | Antigravity and ChatGPT were used to generate and refine initial versions of `src/main.py`, `src/api/routes.py`, `src/api/models.py`, and `src/services/ranking_service.py`.                        |
| **Baseline integration**  | ChatGPT and Claude were used to understand the existing `baseline_3sigma.py` implementation and reason about integrating it into the application architecture.                                      |
| **Documentation**         | ChatGPT and Claude assisted with drafting and structuring `README.md`, `DECISIONS.md`, and `AI-USAGE.md`.                                                                                           |
| **Test scaffolding**      | AI assistants suggested test fixture structures, test cases, and edge cases for the automated test suite.                                                                                           |
| **Debugging**             | Antigravity, ChatGPT, and Claude were used to investigate runtime errors, test failures, timezone issues, and data-handling problems.                                                               |
| **Error handling**        | AI assistants suggested appropriate HTTP status codes and error-handling patterns for API failure conditions.                                                                                       |
| **Code review**           | ChatGPT and Claude were used to review implementation details and identify potential edge cases and inconsistencies.                                                                                |
| **Engineering decisions** | AI assistance was used to structure and articulate engineering decisions documented in `DECISIONS.md`.                                                                                              |

---

## What Was Personally Reviewed

AI-generated suggestions were reviewed during development rather than being accepted without validation.

* The baseline `baseline_3sigma.py` was manually read and understood before wrapping it.
* The ranking logic in `ThreeSigmaRanker` was traced against the original baseline to verify correctness.
* Generated and modified code was reviewed and adjusted where necessary.
* Test cases were reviewed to ensure they tested meaningful application behavior.
* The validation script output was personally checked after major changes.
* API behavior was manually tested using `curl` and the FastAPI `/docs` interactive page.
* `DECISIONS.md` was checked against the actual implementation and development decisions.

---

## How the Implementation Was Tested

The project was validated through both automated and manual testing:

* `python validate_submission.py predictions.csv` was run to validate the prediction pipeline.
* `pytest` was run to verify the automated test suite and detect regressions.
* The API was manually tested using `curl`.
* The FastAPI `/docs` interactive interface was used to test API endpoints.
* Edge cases such as invalid weeks, non-existent gateways, missing data directories, and unusual baseline conditions were tested.
* Tests were re-run after debugging and implementation changes to ensure that existing functionality continued to work.

---

## AI-Assisted Issues and Edge Cases Identified and Corrected

### 1. Constant Baseline `std = 0`

**Issue:**

During baseline analysis and synthetic testing, an edge case was identified where a gateway has zero variance across the 28-day baseline window.

In this situation:

`σ = 0`

and the conventional 3-sigma threshold:

`mean + 3 × std`

becomes equal to the mean. This required explicit consideration because a completely stationary baseline does not provide meaningful variance for conventional 3-sigma anomaly detection.

**How it was caught and tested:**

This case was identified during edge-case analysis and formalized through regression tests:

`tests/test_e2e.py::TestRegressionStdZeroSilentFailure::test_constant_baseline_with_extreme_spike_scores_zero`

and

`test_nonzero_baseline_variance_with_spike_is_flagged`

These tests document the behavior of the implementation for zero-variance and non-zero-variance baselines.

---

### 2. Timezone-Aware Timestamp Handling

**Issue:**

In an initial implementation of `ranking_service.py`, `week_start` could become timezone-naive before being compared with timestamps from the Parquet dataset.

Because the dataset timestamps were timezone-aware UTC timestamps, pandas could raise:

`TypeError: Cannot compare tz-naive and tz-aware`

**Fix applied:**

Dates were normalized to UTC using timezone-aware pandas timestamps:

`pd.Timestamp(week_date, tz="UTC")`

This ensured that date comparisons used consistent timezone information.

The behavior was subsequently covered by the service and API tests.

---

### 3. Offline Swagger UI CDN Dependency

**Issue:**

FastAPI's default Swagger UI documentation depends on external CDN URLs (`cdn.jsdelivr.net`) to load `swagger-ui-bundle.js` and `swagger-ui.css`. When operating in an offline environment (required by the challenge), opening `/docs` failed with `ERR_NAME_NOT_RESOLVED` and javascript errors (`SwaggerUIBundle is not defined`).

**Fix applied:**

Static assets were bundled locally inside `src/static/` and served via FastAPI's `StaticFiles`. The `/docs` handler in `src/main.py` was overridden using `get_swagger_ui_html` pointing exclusively to local `/static/...` assets. A dedicated regression test (`tests/test_api.py::TestOfflineSwagger`) was added to guarantee no external URLs or CDNs are ever referenced in the rendered API documentation.

---

## Role of AI in the Final Implementation

**Antigravity, ChatGPT, and Claude** were used as development assistants throughout different stages of the project. They contributed code suggestions, explanations, debugging assistance, testing ideas, code-review feedback, and documentation support.

The final implementation was not accepted solely on the basis of AI output. The implementation was reviewed, modified where necessary, and validated using automated tests, the submission validation script, and manual API testing.

This disclosure is intended to accurately represent the use of AI during the development of the project.

---

*Last updated: 2026-09-17*
