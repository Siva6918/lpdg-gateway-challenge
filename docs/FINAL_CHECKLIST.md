# Final Submission Checklist — LPDG Innovation Hub Selection Challenge 2026

Use this checklist before marking the submission as complete.  
Each item has a verification command or inspection step.

---

## Part 1 — Gateway Ranking

| # | Item | Command / How to Check | Status |
|---|------|------------------------|--------|
| 1.1 | `predictions.csv` exists at repo root | `ls predictions.csv` | ✅ |
| 1.2 | 120 rows — 15 gateways × 8 weeks | `python validate_submission.py predictions.csv` | ✅ |
| 1.3 | Weeks span 2026-02-02 to 2026-03-23 | Output of validate_submission.py | ✅ |
| 1.4 | Baseline script is unchanged | `git diff 17e3292 baseline_3sigma.py` (should be empty) | ✅ |
| 1.5 | `data/` is NOT committed | `git ls-files data/` (should return nothing) | ✅ |

---

## Part 2 — Software Development

### Code Quality

| # | Item | Command / How to Check | Status |
|---|------|------------------------|--------|
| 2.1 | All 59 tests pass | `python -m pytest` → `59 passed` | ✅ |
| 2.2 | App imports without error | `python -c "from src.main import app; print('OK')"` | ✅ |
| 2.3 | `uvicorn src.main:app --reload` starts on port 8000 | Start server, visit `http://localhost:8000/` | ✅ |
| 2.4 | `/docs` interactive page loads | Browser: `http://localhost:8000/docs` | ✅ |

### API Endpoints

| # | Endpoint | Expected Behaviour | Status |
|---|----------|--------------------|--------|
| 2.5 | `GET /` | `{"status": "ok", ...}` | ✅ |
| 2.6 | `GET /rankings?week=...` valid week | 15 ranked gateways with reasons | ✅ |
| 2.7 | `GET /rankings?week=...` invalid date | HTTP 400 | ✅ |
| 2.8 | `GET /rankings?week=...` out-of-range week | HTTP 400 | ✅ |
| 2.9 | `GET /rankings?week=...` unknown strategy | HTTP 400 | ✅ |
| 2.10 | `GET /gateways/{id}?week=...` known gateway | Rank + diagnostics | ✅ |
| 2.11 | `GET /gateways/{id}?week=...` unknown gateway | HTTP 404 | ✅ |
| 2.12 | `POST /rankings/run` | Re-reads disk, returns summary | ✅ |
| 2.13 | `POST /rankings/run` with bad data_dir | HTTP 503 | ✅ |
| 2.14 | `GET /rankings/weeks` | List of 8 valid weeks | ✅ |
| 2.15 | `GET /strategies` | Includes `three_sigma` as default | ✅ |
| 2.16 | `/run` picks up NEW parquet without restart | `tests/test_new_data.py` — 4 tests | ✅ |

### Architecture Requirements

| # | Item | Where to Verify | Status |
|---|------|-----------------|--------|
| 2.16 | Strategy pattern — new ranker doesn't touch routes | `src/ranking/base.py`, `registry.py` | ✅ |
| 2.17 | Business logic is in service layer, not routes | `src/services/ranking_service.py` | ✅ |
| 2.18 | Pydantic models for all request/response schemas | `src/api/models.py` | ✅ |
| 2.19 | `DATA_DIR` environment variable works | `$env:DATA_DIR="path"; uvicorn src.main:app` | ✅ |

---

## Documentation

| # | File | Required Content | Status |
|---|------|-----------------|--------|
| 3.1 | `README.md` | Part 1 approach, Part 2 architecture, how to run | ✅ |
| 3.2 | `DECISIONS.md` | ≥ 5 engineering decisions with alternatives + reasoning | ✅ |
| 3.3 | `AI-USAGE.md` | Honest disclosure of AI tools + real bug caught | ✅ |
| 3.4 | `requirements.txt` | Pinned versions for all dependencies | ✅ |

---

## Reproducibility

| # | Item | Command | Status |
|---|------|---------|--------|
| 4.1 | Fresh install works | `pip install -r requirements.txt` | ✅ |
| 4.2 | Baseline reruns cleanly | `python baseline_3sigma.py --data data` | ✅ |
| 4.3 | Alternate data dir flag works | `python baseline_3sigma.py --data /other/path` | ✅ |
| 4.4 | API with alternate data dir | `$env:DATA_DIR="other"; uvicorn src.main:app` | ✅ |

---

## Submission Materials

| # | Item | Status |
|---|------|--------|
| 5.1 | Repository is private | ☐ Verify on GitHub |
| 5.2 | Recording is 6–8 minutes and covers all demo steps | ☐ See `docs/RECORDING_SCRIPT.md` |
| 5.3 | Recording link added to `README.md` → Submission Notes | ☐ Add before final submit |
| 5.4 | `git push` — all commits pushed to origin | ☐ `git push` |

---

## Final Git Log (expected)

```
bfad138 Complete project documentation
838f6c7 Make application reproducible
0b4fd80 Add comprehensive tests and regression coverage
ee513c8 Implement Software Development API with error handling
7ffe161 Implement ranking service layer
6c0ee17 Add replaceable ranking strategy
20af138 Set up Software Development architecture
39bd8ce Complete Part 1 documentation
17e3292 Generate and validate Part 1 predictions
```

---

## Known Limitations (documented — not defects)

1. `POST /rankings/run` is synchronous — can be slow on very large datasets
2. No auto-detection of new files in `data/`; must call `POST /rankings/run` manually
3. No authentication — intended as an internal operations tool
4. Ranking algorithm is the provided baseline; no ML improvement was attempted for Part 1

---

*Last updated: 2026-09-11*
