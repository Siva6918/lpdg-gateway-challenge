# Recording Script — LPDG Innovation Hub Selection Challenge 2026

**Target length:** 6–8 minutes  
**Audience:** LPDG evaluation panel  
**Goal:** Demonstrate the complete, running Software Development solution — from cold start to API query — with narration explaining the engineering decisions.

---

## Pre-Recording Checklist (do before hitting Record)

- [ ] `data/` directory is present with telemetry Parquet files
- [ ] Terminal is open in `LPDG-Innovation-Hub/`
- [ ] Browser is open to `http://127.0.0.1:8000/docs` (will start server in recording)
- [ ] Font size bumped up so code is readable in the recording
- [ ] Microphone tested
- [ ] Screen recording software ready

---

## Script

### Section 1 — Introduction (≈ 30 seconds)

> "Hi, I'm [your name], a B.Tech CSE student. This is my submission for the LPDG Innovation Hub Selection Challenge 2026 — Software Development track.
>
> Part 1 uses the provided 3-sigma baseline unchanged and generates `predictions.csv` with 15 gateways for each of the 8 scored weeks. Part 2 is a FastAPI web application that wraps the ranking logic behind a proper software engineering architecture.
>
> Let me show you the whole thing running from scratch."

---

### Section 2 — Repository Tour (≈ 60 seconds)

**Show in IDE / file explorer:**

```
LPDG-Innovation-Hub/
├── predictions.csv       ← Part 1 output (already generated)
├── baseline_3sigma.py    ← challenge baseline, unchanged
├── DECISIONS.md          ← 5 engineering decisions
├── AI-USAGE.md           ← honest AI disclosure
├── requirements.txt
├── src/
│   ├── ranking/          ← Strategy pattern abstraction
│   ├── services/         ← Business logic layer
│   └── api/              ← FastAPI routes + Pydantic models
└── tests/                ← 55 tests across 4 test files
```

> "The architecture follows the Strategy pattern. The API routes depend on a `RankingStrategy` abstract interface. Swapping the algorithm — say, replacing 3-sigma with a gradient boost model — requires only creating a new class. The HTTP layer never changes. This is Decision 3 in DECISIONS.md."

---

### Section 3 — Validate Part 1 (≈ 30 seconds)

```bash
python validate_submission.py predictions.csv
```

Expected output:
```
predictions.csv: OK
  15 ranked gateways for each of 8 weeks, 2026-02-02 to 2026-03-23
```

> "Part 1 passes validation — 120 rows, 15 gateways × 8 weeks."

---

### Section 4 — Run the Tests (≈ 45 seconds)

```bash
python -m pytest -v
```

> "55 tests covering the ranking algorithm, the service layer, all API endpoints, and two regression tests for edge cases we found during development. All green."

---

### Section 5 — Start the API (≈ 30 seconds)

```bash
uvicorn src.main:app --reload
```

> "One command to start. The `--reload` flag restarts automatically if we edit source files. The data directory defaults to `data/` at the project root, but you can override it with the `DATA_DIR` environment variable for a different dataset."

---

### Section 6 — Live API Demo (≈ 3 minutes)

Open a **second terminal** for curl commands. Keep server terminal visible.

#### 6a — Health check
```bash
curl -s http://localhost:8000/ | python -m json.tool
```
> "Simple health check confirms the service is up."

#### 6b — Get this week's rankings
```bash
curl -s "http://localhost:8000/rankings/2026-02-02" | python -m json.tool
```
> "The top 15 gateways for Week 1. Each entry has a rank, gateway ID, anomaly score, and a human-readable reason. The dispatcher reads this reason to know what to look for on site."

#### 6c — Explain a specific gateway
```bash
# Use the first gateway_id from the rankings response above
curl -s "http://localhost:8000/rankings/2026-02-02/0A2778A31BE3" | python -m json.tool
```
> "The explanation endpoint gives diagnostic detail: how many sigma above baseline, which metric triggered, over how many hours. This makes the recommendation explainable — the dispatcher isn't flying blind."

#### 6d — Re-run the pipeline with new data
```bash
curl -s -X POST "http://localhost:8000/rankings/run" | python -m json.tool
```
> "This is the live session scenario. New data has been dropped in the `data/` directory. One POST reloads everything and reruns all 8 weeks. The response confirms how many weeks and gateways were scored."

#### 6e — Interactive API docs (switch to browser)
Open `http://127.0.0.1:8000/docs`
> "FastAPI auto-generates interactive documentation. The operations team can explore and test the API directly in the browser without any additional tooling."

---

### Section 7 — Wrap Up (≈ 30 seconds)

> "To summarise:
>
> - Part 1: 120-row `predictions.csv`, validated, using the provided baseline unchanged.
> - Part 2: A clean FastAPI application with a Strategy-pattern ranking abstraction, a service layer separating business logic from HTTP concerns, Pydantic request/response validation, 55 automated tests, and one-command startup.
>
> The five engineering decisions — why I used the baseline, why I chose this architecture, why the run endpoint is synchronous — are documented in `DECISIONS.md`. AI usage is disclosed in `AI-USAGE.md`.
>
> Thank you."

---

## Post-Recording

- [ ] Trim the video to 6–8 minutes
- [ ] Upload to the submission platform
- [ ] Add the video link to `README.md` (`Submission Notes` section)

---

*Last updated: 2026-09-11*
