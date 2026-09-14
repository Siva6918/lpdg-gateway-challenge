# Final Submission Checklist — LPDG Innovation Hub Selection Challenge 2026

**Registration ID:** 23091A05T2  
**Deadline:** Wednesday, 16 September 2026, 20:59 IST  
**Last updated:** 2026-09-14

Use this checklist before final submission. Each item shows how it was or can be verified.

> [!IMPORTANT]
> Items marked **MANUAL** require your personal action. Do not substitute automated checks for them.

---

## A — Automatically Verified (run commands to confirm)

### Part 1 — Gateway Ranking

| # | Item | Command | Status |
|---|------|---------|--------|
| A1.1 | `predictions.csv` exists at repo root | `ls predictions.csv` | ✅ PASS |
| A1.2 | 120 rows — 15 gateways × 8 weeks | `python validate_submission.py predictions.csv` | ✅ PASS |
| A1.3 | Weeks span 2026-02-02 to 2026-03-23 | Output of validate_submission.py | ✅ PASS |
| A1.4 | Baseline script unchanged from challenge version | `git diff 17e3292 baseline_3sigma.py` → empty | ✅ PASS |
| A1.5 | `data/` is NOT committed | `git ls-files data/` → empty | ✅ PASS |
| A1.6 | No secrets, API keys, or absolute paths | `git grep -r "C:\\Users\|/home/\|password\|api_key"` → empty | ✅ PASS |

### Part 2 — Software Development

#### Code Quality

| # | Item | Command | Status |
|---|------|---------|--------|
| A2.1 | All 59 tests pass | `python -m pytest tests/ -v` → `59 passed` | ✅ PASS |
| A2.2 | App imports without error | `python -c "from src.main import app; print('OK')"` | ✅ PASS |
| A2.3 | predictions.csv validates | `python validate_submission.py predictions.csv` | ✅ PASS |

#### API Endpoints (live server probe — confirmed 2026-09-14)

| # | Endpoint | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| A2.4 | `GET /` | 200 OK | 200 OK | ✅ PASS |
| A2.5 | `GET /rankings?week=2026-02-02` | 200 — 15 gateways | 200 — 15 gateways | ✅ PASS |
| A2.6 | `GET /rankings?week=hello` | 400 Bad Request | 400 Bad Request | ✅ PASS |
| A2.7 | `GET /rankings?week=2020-01-06` | 400 Bad Request | 400 Bad Request | ✅ PASS |
| A2.8 | `GET /rankings?week=2026-02-02&strategy=bogus` | 400 Bad Request | 400 Bad Request | ✅ PASS |
| A2.9 | `GET /gateways/0A2778A31BE3?week=2026-02-02` | 200 — diagnostics | 200 — diagnostics | ✅ PASS |
| A2.10 | `GET /gateways/FFFFFFFFFFFF?week=2026-02-02` | 404 Not Found | 404 Not Found | ✅ PASS |
| A2.11 | `GET /gateways/0A2778A31BE3?week=notadate` | 400 Bad Request | 400 Bad Request | ✅ PASS |
| A2.12 | `POST /rankings/run` | 200 success | 200 success | ✅ PASS |
| A2.13 | `GET /rankings/weeks` | 200 — week list | 200 — week list | ✅ PASS |
| A2.14 | `GET /strategies` | 200 — three_sigma | 200 — three_sigma | ✅ PASS |
| A2.15 | 422 in Swagger docs | Documentation only, no real 422 | Confirmed doc only | ✅ NOT A BUG |

#### Architecture

| # | Item | Where to Verify | Status |
|---|------|-----------------|--------|
| A2.16 | Strategy pattern — new ranker requires no route changes | `src/ranking/base.py`, `registry.py` | ✅ PASS |
| A2.17 | Business logic in service layer, not routes | `src/services/ranking_service.py` | ✅ PASS |
| A2.18 | Pydantic models for request/response | `src/api/models.py` | ✅ PASS |
| A2.19 | `DATA_DIR` env var works | `src/config.py` | ✅ PASS |
| A2.20 | New data without restart — `POST /run` reloads parquet | `tests/test_new_data.py` — 4 tests | ✅ PASS |

---

## B — Repository Verified by Inspection

| # | Item | Finding | Status |
|---|------|---------|--------|
| B1 | `baseline_3sigma.py` unchanged | `git diff 17e3292 baseline_3sigma.py` → empty | ✅ PASS |
| B2 | `validate_submission.py` unchanged | Unmodified since initial commit | ✅ PASS |
| B3 | No hardcoded laptop paths | Searched codebase | ✅ PASS |
| B4 | No internet dependency at runtime | All data from local filesystem | ✅ PASS |
| B5 | `DECISIONS.md` has 5+ decisions | 5 decisions with alternatives + trade-offs | ✅ PASS |
| B6 | Decision 2 explains Software Development choice | Present in DECISIONS.md | ✅ PASS |
| B7 | `AI-USAGE.md` has 3 tools listed | Antigravity, ChatGPT, Claude | ✅ PASS |
| B8 | Real AI mistake documented | std=0 case + timezone bug | ✅ PASS |
| B9 | Limitations documented in README | 4 limitations listed | ✅ PASS |
| B10 | Resume `23091A05T2.pdf` in repo root | File present, tracked | ✅ PASS |
| B11 | Resume named `<Registration_Id>.pdf` | `23091A05T2.pdf` ✓ | ✅ PASS |
| B12 | Resume NOT inside src/, docs/, tests/ | At repository root | ✅ PASS |
| B13 | README has resume section + online link | Added 2026-09-14 | ✅ PASS |
| B14 | README correct API endpoint paths | Fixed 2026-09-14 | ✅ PASS |
| B15 | `docs/RECORDING_SCRIPT.md` exists | Present with correct URLs | ✅ PASS |
| B16 | No visualizations claimed (none created) | Not applicable | ✅ N/A |
| B17 | Synthetic test fixtures — no real dataset in tests | `tests/conftest.py` + `test_new_data.py` | ✅ PASS |
| B18 | E2E test exists | `tests/test_e2e.py::TestEndToEnd` | ✅ PASS |
| B19 | Regression test for std=0 bug | `tests/test_e2e.py::TestRegressionStdZeroSilentFailure` | ✅ PASS |
| B20 | requirements.txt has pinned versions | Confirmed | ✅ PASS |

---

## C — Manual Tasks (you must do these personally)

| # | Item | When | Done? |
|---|------|------|-------|
| C1 | **Make repository PUBLIC on GitHub** | Before submitting the Google Form | ☐ |
| C2 | **Record 6–8 min demo video** | Before deadline | ☐ |
| C3 | **Add recording link to README** (`Submission Notes` section) | After recording | ☐ |
| C4 | **`git push`** after adding recording link | After C3 | ☐ |
| C5 | **Submit the official Google Form** | Before 16 Sep 2026, 20:59 IST | ☐ |
| C6 | **Practice live session demo** | Before evaluation | ☐ |
| C7 | Verify GitHub repo is private until submitting | Before C1 | ☐ |
| C8 | Verify GitHub shows `23091A05T2.pdf` at repo root | After push | ☐ |
| C9 | Manually test API with real data: `uvicorn src.main:app --reload` | Before recording | ☐ |
| C10 | Practice the new-data-without-restart demo live | Before evaluation | ☐ |

---

## D — Demo Commands (copy-paste for recording / live session)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Validate Part 1
python validate_submission.py predictions.csv

# 3. Run all tests
python -m pytest tests/ -v

# 4. Start API
uvicorn src.main:app --reload

# 5. In a second terminal:
curl http://localhost:8000/
curl "http://localhost:8000/rankings?week=2026-02-02"
curl "http://localhost:8000/gateways/0A2778A31BE3?week=2026-02-02"
curl -X POST http://localhost:8000/rankings/run
curl http://localhost:8000/rankings/weeks
curl http://localhost:8000/strategies
```

### New-data-without-restart demo:
```bash
# Server already running...
# 1. Copy new month parquet into data/telemetry/
# 2. Call run (no restart):
curl -X POST http://localhost:8000/rankings/run
# 3. Query new week:
curl "http://localhost:8000/rankings?week=2026-04-06"
```

---

## E — Actual Git Log (as of 2026-09-14)

```
8ecf03f (HEAD -> main, origin/main) Add new-data-without-restart tests and fix docs
7ec5e19  AI tools added ChatGPT and Claude
ff18662  Prepare final submission materials
f798f1c  Complete project documentation
0b4fd80  Add comprehensive tests and regression coverage
ee513c8  Implement Software Development API with error handling
7ffe161  Implement ranking service layer
6c0ee17  Add replaceable ranking strategy
20af138  Set up Software Development architecture
39bd8ce  Complete Part 1 documentation
17e3292  Generate and validate Part 1 predictions
db2412c  Project Setup
```

---

## F — Known Limitations (documented — not defects)

1. `POST /rankings/run` is synchronous — can be slow on very large datasets
2. New files are not auto-detected; `POST /rankings/run` must be called manually
3. No authentication — intended as an internal operations tool
4. Ranking uses the provided 3-sigma baseline; no ML improvement was attempted for Part 1

---

## G — Submission Requirements Checklist

From the official participant instructions:

| Requirement | Status |
|-------------|--------|
| Deadline: 16 Sep 2026, 20:59 IST | ☐ MANUAL — submit before deadline |
| Submit via official Google Form | ☐ MANUAL — you submit the form |
| First submission is final (no duplicates) | ☐ MANUAL — submit only once |
| GitHub repository must be PUBLIC for evaluation | ☐ MANUAL — make public before submitting |
| Everything in the repository | ✅ All code, docs, resume, predictions |
| Resume in repo root as `<Registration_Id>.pdf` | ✅ `23091A05T2.pdf` present and committed |
| Documentation in README | ✅ README complete |
| Visualizations in README (if any) | ✅ N/A — no visualizations |
| In-person evaluation (live session) | ☐ MANUAL — attend if invited |
