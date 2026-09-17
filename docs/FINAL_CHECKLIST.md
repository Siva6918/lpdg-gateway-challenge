# Final Submission Checklist — LPDG Innovation Hub Selection Challenge 2026

**Registration ID:** 23091A05T2  
**Official Email:** 23091a05t2@rgmcet.edu.in  
**Submission Deadline:** Wednesday, 16 September 2026, 20:00 IST  
**Evaluation:** Friday, 18 September 2026, 9:30 AM onwards at RGMCET campus (arrive by 9:00 AM)  
**Submission Form:** https://forms.gle/qHZqsrRPGWf8ja5S6  

---

## Status Classification Guide

- **[VERIFIED]**: Verified programmatically or by filesystem/git inspection in the local repository.
- **[NEEDS MANUAL ACTION]**: Requires explicit manual action by the participant (e.g. form submission, attending evaluation, pushing).
- **[NOT VERIFIABLE]**: External service state that cannot be verified locally from the repository environment (e.g. GitHub repository public visibility on the web).

---

## PART 1: Gateway Ranking

- [x] **predictions.csv** — [VERIFIED] Exists at repository root.
- [x] **120 rows** — [VERIFIED] Exactly 120 prediction rows present.
- [x] **8 required weeks** — [VERIFIED] Covers 2026-02-02, 2026-02-09, 2026-02-16, 2026-02-23, 2026-03-02, 2026-03-09, 2026-03-16, 2026-03-23.
- [x] **15 gateways/week** — [VERIFIED] Exactly 15 unique gateways ranked per week.
- [x] **ranks 1–15** — [VERIFIED] Ranks 1 to 15 per week without gaps or duplicates.
- [x] **reasons valid** — [VERIFIED] All reason strings non-empty and within length limits.
- [x] **validator passes** — [VERIFIED] `python validate_submission.py predictions.csv` passes with `OK`.
- [x] **baseline deterministic** — [VERIFIED] `baseline_3sigma.py` implements deterministic tie-breaking (primary `flagged_hours` descending, secondary `gateway_id` ascending).
- [x] **data not committed** — [VERIFIED] `data/` excluded in `.gitignore` and untracked in `git ls-files data/`.

---

## DOCUMENTATION

- [x] **README.md** — [VERIFIED] Complete with required problem statement, track description, endpoints, and setup.
- [x] **DECISIONS.md** — [VERIFIED] Contains 6 engineering decisions, trade-offs, and Track selection rationale.
- [x] **AI-USAGE.md** — [VERIFIED] Discloses Antigravity, ChatGPT, Claude, and documents real caught errors (`std=0`, timestamp tz, offline Swagger).
- [x] **limitations** — [VERIFIED] Documented in both `README.md` and `DECISIONS.md`.
- [x] **two-week improvement plan** — [VERIFIED] Documented in both `README.md` and `DECISIONS.md`.
- [x] **API documentation** — [VERIFIED] Comprehensive endpoint tables and curl examples in `README.md`, plus `/docs` OpenAPI.
- [x] **project structure** — [VERIFIED] Directory tree documented in `README.md`.
- [x] **demo video link** — [VERIFIED] Included in `README.md`: https://drive.google.com/file/d/1NZrH55AloQklucSVIiltkQyHVW1Rp_fC/view?usp=sharing
- [x] **portfolio link** — [VERIFIED] Included in `README.md`: https://portfolio-azure-theta-94.vercel.app/workspace/work/lpdg_submission-mp4

---

## PART 2: Software Development

- [x] **API works** — [VERIFIED] Tested via FastAPI TestClient and pytest suite (`73 passed`).
- [x] **weekly top 15** — [VERIFIED] `GET /rankings?week=YYYY-MM-DD` returns 15 gateways with scores and reasons.
- [x] **gateway explanation** — [VERIFIED] `GET /gateways/{gateway_id}?week=YYYY-MM-DD` provides diagnostic breakdown.
- [x] **rerun endpoint** — [VERIFIED] `POST /rankings/run` reloads telemetry and refreshes cache.
- [x] **error handling** — [VERIFIED] 400 (invalid date/week/strategy/no data in window), 404 (unknown gateway), 422 (corrupt/empty telemetry), 503 (missing data dir) covered and tested.
- [x] **determinism tests** — [VERIFIED] `tests/test_determinism.py` verifies repeated rankings, row-order invariance, and tie-breaking.
- [x] **E2E tests** — [VERIFIED] `tests/test_e2e.py` verifies end-to-end workflow.
- [x] **regression test** — [VERIFIED] `tests/test_e2e.py::TestRegressionStdZeroSilentFailure` tests `std=0` edge case; `tests/test_api.py::TestOfflineSwagger` verifies zero CDN URLs in `/docs`.
- [x] **synthetic fixtures** — [VERIFIED] Tests run on fast synthetic data without requiring 104 MB challenge files.
- [x] **new data without restart** — [VERIFIED] `tests/test_new_data.py` verifies loading new month parquet on disk without restarting process.
- [x] **new gateway IDs handled** — [VERIFIED] Unseen gateway IDs in new data are ingested without crashes.
- [x] **replaceable ranking strategy** — [VERIFIED] Abstract `RankingStrategy` and `registry.py` decouple algorithms from route handlers.
- [x] **API docs offline** — [VERIFIED] FastAPI Swagger UI available at `/docs` backed by local bundled assets (`src/static/`).

---

## SUBMISSION & PRE-FLIGHT

- [ ] **public GitHub repository** — [NOT VERIFIABLE / NEEDS MANUAL ACTION] Verify GitHub repo settings are set to **PUBLIC** before submitting form.
- [x] **resume 23091A05T2.pdf** — [VERIFIED] Present at repository root and tracked by git.
- [x] **repository contains required artifacts** — [VERIFIED] `predictions.csv`, `23091A05T2.pdf`, `README.md`, `DECISIONS.md`, `AI-USAGE.md`.
- [x] **no dataset committed** — [VERIFIED] `data/` is strictly ignored and untracked.
- [x] **no secrets** — [VERIFIED] No API keys, credentials, or `.env` files committed.
- [ ] **demo recording ready** — [NEEDS MANUAL ACTION] Verify playback of the Google Drive demo link in an incognito window.
- [x] **demo link in README** — [VERIFIED] Google Drive demo link included in `README.md`.
- [x] **portfolio link in README** — [VERIFIED] Portfolio link included in `README.md`.
- [ ] **Google Form ready** — [NEEDS MANUAL ACTION] Submit form (https://forms.gle/qHZqsrRPGWf8ja5S6) before deadline.
- [x] **official RGMCET email** — [VERIFIED] `23091a05t2@rgmcet.edu.in` documented in `README.md` and checklist.
- [x] **registration ID 23091A05T2** — [VERIFIED] Consistent throughout files and resume naming.
- [x] **deadline 16 Sep 2026, 20:00 IST** — [VERIFIED] Documented and acknowledged as authoritative.
- [ ] **evaluation 18 Sep 2026** — [NEEDS MANUAL ACTION] Attend evaluation at RGMCET campus (arrive by 9:00 AM for 9:30 AM start).

---

*Last verified: 2026-09-17*
